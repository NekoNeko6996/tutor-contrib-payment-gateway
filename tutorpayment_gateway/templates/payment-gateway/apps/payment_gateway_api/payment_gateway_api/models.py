# tutorpayment_gateway/templates/payment-gateway/apps/payment_gateway_api/payment_gateway_api/models.py
import uuid
from django.conf import settings
from django.db import models

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING  = "PENDING"
        PAID     = "PAID"
        FAILED   = "FAILED"
        CANCELED = "CANCELED"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    course_id = models.CharField(max_length=255)
    mode = models.CharField(max_length=32, default="verified")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="VND")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=32, blank=True)
    external_txn_id = models.CharField(max_length=128, blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["uid", "status", "course_id"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.uid} - {self.user} - {self.course_id} - {self.status}"
