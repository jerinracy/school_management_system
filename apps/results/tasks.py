"""Celery tasks for asynchronous result tabulation and annual cumulative CGPA processing."""

import logging
from typing import Any

from celery import shared_task

from apps.results.services import tabulate_cumulative_results, tabulate_exam_results

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def calculate_exam_results_task(self, exam_id: str) -> dict[str, Any]:
    """Background task to tabulate and rank student results for an examination."""
    try:
        result = tabulate_exam_results(exam_id=exam_id)
        logger.info("Successfully tabulated results for exam %s: %s", exam_id, result)
        return result
    except Exception as exc:
        logger.error("Failed to tabulate exam results for exam %s: %s", exam_id, exc)
        raise self.retry(exc=exc, countdown=15) from exc


@shared_task(bind=True, max_retries=2)
def calculate_cumulative_results_task(self, session_id: str, class_level_id: str) -> dict[str, Any]:
    """Background task to compute annual cumulative session CGPA for a class."""
    try:
        result = tabulate_cumulative_results(session_id=session_id, class_level_id=class_level_id)
        logger.info(
            "Successfully computed cumulative results for session %s and class %s: %s",
            session_id,
            class_level_id,
            result,
        )
        return result
    except Exception as exc:
        logger.error(
            "Failed cumulative tabulation for session %s and class %s: %s",
            session_id,
            class_level_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=15) from exc
