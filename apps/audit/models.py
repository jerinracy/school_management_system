"""Immutable AuditLog and ActivityLog models."""

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    SOFT_DELETE = "soft_delete", "Soft Delete"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    LOGIN_FAILED = "login_failed", "Login Failed"
    ROLE_CHANGE = "role_change", "Role Change"
    PERMISSION_CHANGE = "permission_change", "Permission Change"
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    OVERRIDE = "override", "Override"
    EXPORT = "export", "Export"
    CONSENT_CHANGE = "consent_change", "Consent Change"
    PAYMENT = "payment", "Payment"


class ImmutableAuditModel(models.Model):
    """Abstract base ensuring rows are append-only (no ORM updates or deletes)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError(f"{self.__class__.__name__} records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError(f"{self.__class__.__name__} records cannot be deleted.")


class AuditLog(ImmutableAuditModel):
    """Immutable audit trail for sensitive model & security state changes."""

    institution = models.ForeignKey(
        "institutions.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_logs",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(
        max_length=32,
        choices=AuditAction.choices,
        db_index=True,
    )
    module = models.CharField(max_length=64, db_index=True)
    target_model = models.CharField(max_length=100, db_index=True)
    target_object_id = models.CharField(max_length=64, blank=True, db_index=True)
    target_repr = models.CharField(max_length=255, blank=True)
    before_data = models.JSONField(default=dict, blank=True)
    after_data = models.JSONField(default=dict, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(ImmutableAuditModel.Meta):
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["institution", "created_at"]),
            models.Index(fields=["institution", "module", "action"]),
            models.Index(fields=["target_model", "target_object_id"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.module}.{self.action} on {self.target_model}:{self.target_object_id}"


class ActivityLog(ImmutableAuditModel):
    """Immutable user activity log for logins, exports, and operational tracking."""

    institution = models.ForeignKey(
        "institutions.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="activity_logs",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    activity_type = models.CharField(max_length=64, db_index=True)
    module = models.CharField(max_length=64, db_index=True)
    description = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(ImmutableAuditModel.Meta):
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=["institution", "created_at"]),
            models.Index(fields=["institution", "activity_type"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.actor_username}: {self.activity_type}"
