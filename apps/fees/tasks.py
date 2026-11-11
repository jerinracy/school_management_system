"""Celery background tasks for billing and fine accrual."""

from typing import Any

from celery import shared_task

from apps.academics.models import ClassLevel
from apps.fees.services.fine_service import evaluate_overdue_invoices_batch
from apps.fees.services.invoice_service import generate_bulk_invoices
from apps.institutions.models import AcademicSession, Institution


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_bulk_invoices_task(
    self: Any,
    institution_id: str,
    session_id: str,
    class_level_id: str,
    section_id: str | None = None,
    billing_month: int | None = None,
    billing_year: int = 2026,
    invoice_type: str = "monthly",
    as_issued: bool = True,
) -> dict[str, Any]:
    """Background task to generate bulk invoices for an entire class/section."""
    try:
        institution = Institution.objects.get(id=institution_id)
        session = AcademicSession.objects.get(id=session_id)
        class_level = ClassLevel.objects.get(id=class_level_id)

        res = generate_bulk_invoices(
            institution=institution,
            session=session,
            class_level=class_level,
            section_id=section_id,
            billing_month=billing_month,
            billing_year=billing_year,
            invoice_type=invoice_type,
            as_issued=as_issued,
        )
        return res
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def calculate_overdue_fines_task(self: Any, institution_id: str) -> dict[str, Any]:
    """Background cron task to evaluate late fines on overdue invoices."""
    try:
        count = evaluate_overdue_invoices_batch(institution_id=institution_id)
        return {"institution_id": institution_id, "updated_invoices": count}
    except Exception as exc:
        raise self.retry(exc=exc) from exc
