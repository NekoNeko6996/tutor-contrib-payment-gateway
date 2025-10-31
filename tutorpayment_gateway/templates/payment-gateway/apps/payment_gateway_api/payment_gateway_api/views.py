# payment_gateway_api/views.py
from django.utils import timezone
from urllib.parse import unquote
from decimal import Decimal
from typing import Any, Dict, List
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required, user_passes_test
from opaque_keys.edx.keys import CourseKey
from common.djangoapps.course_modes.models import CourseMode
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

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
        # Bỏ các mode free
        if m.mode_slug in {"audit", "honor"}:
            continue
        # Tính hết hạn
        try:
            expires = m.expiration_datetime  # property
        except Exception:
            expires = None
        is_expired = expires is not None and expires <= now
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
            "is_expired": is_expired,
        })

    # Chỉ giữ mode có giá trị “trả phí”
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
