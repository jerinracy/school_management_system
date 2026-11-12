"""Celery background tasks for Homework notifications and due-soon reminders."""

from typing import Any

from celery import shared_task

from apps.homework.models import Homework
from apps.homework.services.homework_service import publish_homework, send_due_soon_reminders
from apps.institutions.models import Institution


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def send_homework_due_soon_reminders_task(
    self: Any,
    institution_id: str | None = None,
    hours_ahead: int = 24,
) -> int:
    """Periodic idempotent task notifying students/guardians of homework due soon."""
    institution = Institution.objects.filter(id=institution_id).first() if institution_id else None
    return send_due_soon_reminders(institution=institution, hours_ahead=hours_ahead)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def notify_homework_published_task(self: Any, homework_id: str) -> str:
    """Async wrapper ensuring a homework is published and notifications dispatched."""
    hw = Homework.objects.filter(id=homework_id, is_deleted=False).first()
    if not hw:
        return "not_found"
    publish_homework(hw)
    return "published"
