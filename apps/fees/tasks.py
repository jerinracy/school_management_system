"""Celery background tasks for billing, fine accrual, and payment reconciliation."""

from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.academics.models import ClassLevel
from apps.fees.gateways import get_gateway_adapter
from apps.fees.models import Payment, PaymentStatus
from apps.fees.services.fine_service import evaluate_overdue_invoices_batch
from apps.fees.services.invoice_service import generate_bulk_invoices
from apps.fees.services.payment_service import complete_online_payment
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


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def reconcile_pending_payments_task(
    self: Any,
    institution_id: str | None = None,
    older_than_minutes: int = 15,
) -> dict[str, Any]:
    """Background task to query gateway status or expire stale pending payments."""
    try:
        cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
        qs = Payment.objects.filter(
            status__in=[PaymentStatus.INITIATED, PaymentStatus.PENDING],
            created_at__lte=cutoff,
        )
        if institution_id:
            qs = qs.filter(institution_id=institution_id)

        reconciled_count = 0
        failed_count = 0

        for payment in qs:
            try:
                adapter = get_gateway_adapter(payment.payment_method)
                ver_params = {
                    "val_id": payment.gateway_order_id or payment.transaction_id,
                    "tran_id": payment.gateway_order_id,
                    "payment_id": payment.gateway_order_id,
                    "mer_txnid": payment.gateway_order_id,
                    "transaction_id": payment.transaction_id or str(payment.id),
                }
                ver_result = adapter.verify(payment, ver_params)
                if ver_result.get("is_valid"):
                    complete_online_payment(payment, ver_params)
                    reconciled_count += 1
                elif payment.created_at <= timezone.now() - timedelta(minutes=60):
                    payment.status = PaymentStatus.FAILED
                    payment.save(update_fields=["status", "updated_at"])
                    failed_count += 1
            except Exception:
                if payment.created_at <= timezone.now() - timedelta(minutes=60):
                    payment.status = PaymentStatus.FAILED
                    payment.save(update_fields=["status", "updated_at"])
                    failed_count += 1

        return {
            "processed": qs.count(),
            "reconciled": reconciled_count,
            "failed": failed_count,
        }
    except Exception as exc:
        raise self.retry(exc=exc) from exc
