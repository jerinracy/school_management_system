"""Celery tasks for asynchronous result tabulation, report cards, and broadsheet generation."""

import logging
from typing import Any

from celery import shared_task

from apps.accounts.models import User
from apps.results.services import (
    create_tabulation_sheet_record,
    generate_bulk_report_cards_zip,
    tabulate_cumulative_results,
    tabulate_exam_results,
)

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


@shared_task(bind=True, max_retries=2)
def generate_tabulation_sheet_task(
    self,
    exam_id: str,
    class_level_id: str,
    section_id: str | None = None,
    file_format: str = "xlsx",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Background task to generate and persist a TabulationSheet document."""
    try:
        user = User.objects.filter(id=user_id).first() if user_id else None
        record = create_tabulation_sheet_record(
            exam_id=exam_id,
            class_level_id=class_level_id,
            section_id=section_id,
            file_format=file_format,
            user=user,
        )
        logger.info("Successfully generated tabulation sheet %s (v%s)", record.id, record.version)
        return {
            "status": "success",
            "tabulation_sheet_id": str(record.id),
            "version": record.version,
            "total_students": record.total_students,
        }
    except Exception as exc:
        logger.error("Failed to generate tabulation sheet: %s", exc)
        raise self.retry(exc=exc, countdown=15) from exc


@shared_task(bind=True, max_retries=2)
def generate_bulk_report_cards_task(
    self,
    exam_id: str,
    class_level_id: str,
    section_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Background task to batch-generate report cards for a class/section."""
    try:
        user = User.objects.filter(id=user_id).first() if user_id else None
        zip_bytes = generate_bulk_report_cards_zip(
            exam_id=exam_id,
            class_level_id=class_level_id,
            section_id=section_id,
            user=user,
        )
        logger.info(
            "Successfully batch generated report cards for exam %s, class %s (size: %s bytes)",
            exam_id,
            class_level_id,
            len(zip_bytes),
        )
        return {
            "status": "success",
            "exam_id": exam_id,
            "class_level_id": class_level_id,
            "archive_size_bytes": len(zip_bytes),
        }
    except Exception as exc:
        logger.error("Failed bulk report card generation: %s", exc)
        raise self.retry(exc=exc, countdown=15) from exc
