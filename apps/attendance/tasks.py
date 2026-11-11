"""Celery tasks for async raw punch processing and end-of-day absentee marking."""

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.attendance.services import mark_daily_absentees_for_date, process_raw_punches
from apps.institutions.models import Institution

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_unprocessed_raw_punches_task(self) -> dict[str, int]:
    """Background task processing batches of unprocessed hardware punches."""
    total_events = 0
    total_punches = 0

    try:
        events, punches = process_raw_punches(batch_size=500)
        total_events += events
        total_punches += punches
    except Exception as exc:
        logger.error("Error processing raw punches in Celery task: %s", exc)
        raise self.retry(exc=exc, countdown=30) from exc

    return {"events_created": total_events, "punches_processed": total_punches}


@shared_task(bind=True)
def mark_daily_absentees_task(
    self,
    institution_id: str | None = None,
    target_date_str: str | None = None,
) -> dict[str, Any]:
    """Scheduled EOD job marking absentees, holidays, and weekends for unrecorded persons."""
    parsed = parse_date(target_date_str) if target_date_str else None
    target_date = parsed if parsed is not None else timezone.localdate()
    total_marked = 0

    institutions = Institution.objects.all()
    if institution_id:
        institutions = institutions.filter(id=institution_id)

    for inst in institutions:
        try:
            count = mark_daily_absentees_for_date(institution=inst, target_date=target_date)
            total_marked += count
        except Exception as exc:
            logger.error(
                "Error marking absentees for institution %s on %s: %s", inst.id, target_date, exc
            )

    return {"marked_count": total_marked, "date": str(target_date)}
