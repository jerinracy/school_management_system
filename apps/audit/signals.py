"""Signal receivers connecting sensitive models to AuditLog."""

from typing import Any

from django.apps import apps
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction
from apps.audit.services.audit_service import record


@receiver(post_save, sender=UserRole)
def audit_user_role_saved(
    sender: type[UserRole],
    instance: UserRole,
    created: bool,
    **kwargs: Any,
) -> None:
    record(
        action=AuditAction.ROLE_CHANGE,
        module="accounts",
        target_model="UserRole",
        target_object_id=instance.id,
        target_repr=f"User={instance.user_id} Role={instance.role_id}",
        after_data={
            "user_id": str(instance.user_id),
            "role_id": str(instance.role_id),
            "role_code": getattr(instance.role, "code", ""),
            "created": created,
        },
        institution=getattr(instance.user, "institution", None),
    )


@receiver(post_delete, sender=UserRole)
def audit_user_role_deleted(
    sender: type[UserRole],
    instance: UserRole,
    **kwargs: Any,
) -> None:
    record(
        action=AuditAction.ROLE_CHANGE,
        module="accounts",
        target_model="UserRole",
        target_object_id=instance.id,
        target_repr=f"Revoked User={instance.user_id} Role={instance.role_id}",
        before_data={
            "user_id": str(instance.user_id),
            "role_id": str(instance.role_id),
        },
        institution=getattr(instance.user, "institution", None),
    )


def _connect_optional_signal(app_label: str, model_name: str, module_name: str) -> None:
    try:
        model_cls = apps.get_model(app_label, model_name)
    except LookupError:
        return

    def _on_save(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
        inst = getattr(instance, "institution", None)
        status_val = str(getattr(instance, "status", ""))
        action = AuditAction.CREATE if created else AuditAction.UPDATE
        if status_val == "approved":
            action = AuditAction.APPROVE
        elif status_val == "rejected":
            action = AuditAction.REJECT

        record(
            action=action,
            module=module_name,
            target_model=model_name,
            target_object_id=getattr(instance, "id", ""),
            target_repr=str(instance)[:255],
            after_data={"status": status_val} if status_val else {},
            institution=inst,
        )

    post_save.connect(_on_save, sender=model_cls, weak=False)


_connect_optional_signal("attendance", "AttendanceCorrection", "attendance")
_connect_optional_signal("results", "ResultPublication", "results")
_connect_optional_signal("fees", "PaymentTransaction", "fees")
