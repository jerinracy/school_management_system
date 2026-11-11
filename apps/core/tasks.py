"""Core Celery background tasks."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="apps.core.tasks.health_check_task")
def health_check_task(self: object) -> dict[str, str]:
    """Asynchronous health check task to verify Celery worker connectivity."""
    now = timezone.now().isoformat()
    logger.info("Celery health check task executed at %s", now)
    return {
        "status": "ok",
        "task_name": "apps.core.tasks.health_check_task",
        "executed_at": now,
    }
