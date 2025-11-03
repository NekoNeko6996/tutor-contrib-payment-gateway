# payment_gateway_api/views.py
import json, hmac, hashlib
from decimal import Decimal
from typing import Any, Dict, List
from urllib.parse import unquote

import requests
from django.conf import settings
from django.http import (
    JsonResponse, HttpResponseBadRequest, HttpResponse, HttpResponseForbidden
)
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from opaque_keys.edx.keys import CourseKey
from common.djangoapps.course_modes.models import CourseMode
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from common.djangoapps.student.models import CourseEnrollment

from .models import Order

# ===== helpers =====
def _decimal(v: Any) -> float:
    if v is None: return 0.0
    if isinstance(v, Decimal): return float(v)
    try: return float(v)
    except Exception: return 0.0

def _normalize_course_id(s: str) -> str:
    s = unquote((s or "").strip())
    if s.startswith("course-v1:") and " " in s and "+" not in s:
        s = s.replace(" ", "+")
    return s

def _coerce_course_key(course_id: str) -> CourseKey:
    return CourseKey.from_string(course_id)

def _modes_for_course(course_key: CourseKey) -> List[Dict[str, Any]]:
    qs = CourseMode.objects.filter(course_id=course_key)
    now = timezone.now()
    out: List[Dict[str, Any]] = []
    for m in qs:
        # Bỏ free modes
        if m.mode_slug in {"audit", "honor"}:
            continue
        # Hết hạn: dùng expiration_date / expiration_datetime nếu có
        try:
            expires = getattr(m, "expiration_datetime", None)
        except Exception:
            expires = None
        is_expired = bool(expires and expires <= now)
        # fallback theo date
        if not expires and getattr(m, "expiration_date", None):
            is_expired = timezone.now().date() > m.expiration_date

        if is_expired:
            continue

        suggested = getattr(m, "suggested_prices", None)
        if isinstance(suggested, (list, tuple)):
            suggested_list = [_decimal(x) for x in suggested]
        else:
            suggested_list = []

        out.append({
            "slug": m.mode_slug,
            "name": getattr(m, "mode_display_name", m.mode_slug) or m.mode_slug,
            "currency": getattr(m, "currency", None),
            "min_price": _decimal(getattr(m, "min_price", None)),
            "suggested_prices": suggested_list,
            "sku": getattr(m, "sku", None) or getattr(m, "android_sku", None)
                   or getattr(m, "ios_sku", None) or getattr(m, "bulk_sku", None),
            "expiration_datetime": expires.isoformat() if expires else None,
        })

    # Chỉ giữ mode có giá trị trả phí
    return [r for r in out if r["min_price"] > 0 or r["sku"] or r["currency"]]

def _course_meta(course_key: CourseKey) -> Dict[str, Any]:
    meta = {"course_id": str(course_key), "course_name": None,
            "course_start": None, "course_end": None,
            "enrollment_start": None, "enrollment_end": None,
            "invite_only": None}
    try:
        co = CourseOverview.get_from_id(course_key)
        meta.update({
            "course_name": co.display_name_with_default,
            "course_start": co.start.isoformat() if co.start else None,
            "course_end": co.end.isoformat() if co.end else None,
            "enrollment_start": co.enrollment_start.isoformat() if co.enrollment_start else None,
            "enrollment_end": co.enrollment_end.isoformat() if co.enrollment_end else None,
            "invite_only": bool(co.invite_only),
        })
    except Exception:
        pass
    return meta

def _is_staff(u):
    return u.is_authenticated and (u.is_staff or u.is_superuser)

def _price_and_currency(course_key: CourseKey, mode_slug: str):
    m = CourseMode.objects.get(course_id=course_key, mode_slug=mode_slug)
    # Hết hạn:
    if m.expiration_date and timezone.now().date() > m.expiration_date:
        raise ValueError("Course mode expired")
    return Decimal(m.min_price or 0), (m.currency or "VND")

def _hmac(secret: str, payload: bytes) -> str:
    import hashlib, hmac
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

def _finalize_paid(order: Order, external_txn_id: str = ""):
    if order.status == Order.Status.PAID:
        return
    order.status = Order.Status.PAID
    if external_txn_id:
        order.external_txn_id = external_txn_id
    order.save(update_fields=["status", "external_txn_id", "updated_at"])
    # Enroll
    ck = CourseKey.from_string(order.course_id)
    CourseEnrollment.enroll(order.user, ck, order.mode)

# ===== Endpoints: Pricing (staff-only) =====
@require_GET
@login_required
@user_passes_test(_is_staff)
def course_price(request):
    cid = _normalize_course_id(request.GET.get("course_id") or request.GET.get("course"))
    if not cid:
        return HttpResponseBadRequest("Missing course_id")
    try:
        course_key = _coerce_course_key(cid)
    except Exception:
        return HttpResponseBadRequest("Invalid course_id")
    data = _course_meta(course_key)
    data["modes"] = _modes_for_course(course_key)
    return JsonResponse(data)

@require_GET
@login_required
@user_passes_test(_is_staff)
def course_price_by_path(request, course_id: str):
    cid = _normalize_course_id(course_id)
    try:
        course_key = _coerce_course_key(cid)
    except Exception:
        return HttpResponseBadRequest("Invalid course_id")
    data = _course_meta(course_key)
    data["modes"] = _modes_for_course(course_key)
    return JsonResponse(data)

# ===== Endpoints: Thanh toán tối thiểu =====
@login_required
def checkout(request):
    course_id = _normalize_course_id(request.GET.get("course_id"))
    mode = request.GET.get("mode", "verified")
    if not course_id:
        return HttpResponseBadRequest("Missing course_id")
    try:
        ck = _coerce_course_key(course_id)
        amount, currency = _price_and_currency(ck, mode)
    except Exception as ex:
        return HttpResponseBadRequest(f"Invalid course/mode: {ex}")

    order = Order.objects.create(
        user=request.user, course_id=course_id, mode=mode,
        amount=amount, currency=currency, status=Order.Status.PENDING, provider="vnpay",
    )

    payload = {
        "order_uid": str(order.uid),
        "amount": str(order.amount),
        "currency": order.currency,
        "provider": order.provider,
        "return_url": request.build_absolute_uri(f"/payment-gateway/return/{order.uid}"),
        "customer": {"username": request.user.username, "email": request.user.email or ""},
        "meta": {"course_id": order.course_id, "mode": order.mode},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()

    try:
        node_url = settings.PAYMENT_NODE_CREATE_URL
        secret = settings.PAYMENT_SHARED_SECRET
    except Exception:
        return HttpResponseBadRequest("Payment settings not configured")

    try:
        r = requests.post(
            node_url, data=raw,
            headers={"Content-Type": "application/json", "X-Signature": _hmac(secret, raw)},
            timeout=15
        )
    except Exception as ex:
        return HttpResponse(f"Cannot reach payment service: {ex}", status=502)

    if r.status_code != 200:
        return HttpResponse(f"Create payment failed: {r.text}", status=502)

    data = r.json()
    checkout_url = data["checkout_url"]
    if "txn_id" in data:
        order.external_txn_id = data["txn_id"]
        order.save(update_fields=["external_txn_id", "updated_at"])

    return redirect(checkout_url)

@csrf_exempt
def confirm(request):
    raw = request.body
    try:
        secret = settings.PAYMENT_SHARED_SECRET
    except Exception:
        return HttpResponseBadRequest("Payment settings not configured")

    sig = request.headers.get("X-Signature", "")
    if sig != _hmac(secret, raw):
        return HttpResponseForbidden("Bad signature")

    try:
        data = json.loads(raw.decode())
        order = get_object_or_404(Order, uid=data["order_uid"])
        if str(order.amount) != str(data.get("amount")) or order.currency != data.get("currency"):
            return HttpResponseBadRequest("Amount/currency mismatch")

        status = data.get("status")
        if status == "success":
            _finalize_paid(order, external_txn_id=data.get("txn_id",""))
        elif status in ("failed", "canceled"):
            order.status = Order.Status.FAILED if status=="failed" else Order.Status.CANCELED
            order.save(update_fields=["status", "updated_at"])
        else:
            return HttpResponseBadRequest("Unknown status")
        return JsonResponse({"ok": True})
    except Exception as ex:
        return HttpResponseBadRequest(f"Error: {ex}")

def return_page(request, uid):
    order = get_object_or_404(Order, uid=uid)
    if order.status == Order.Status.PAID:
        msg = "Thanh toán thành công. Bạn đã được ghi danh."
    elif order.status in (Order.Status.FAILED, Order.Status.CANCELED):
        msg = "Thanh toán không thành công hoặc đã hủy."
    else:
        msg = "Giao dịch đang được xử lý. Vui lòng tải lại trang sau ít phút."
    return HttpResponse(msg)
