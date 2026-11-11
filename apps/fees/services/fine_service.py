"""Late payment fine evaluation and accrual."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.fees.models import FineRule, FineType, Invoice, InvoiceStatus


def _calculate_fine_by_type(fine_rule: FineRule, days_overdue: int) -> Decimal:
    """Calculate raw fine according to rule type."""
    if fine_rule.fine_type == FineType.FIXED:
        return fine_rule.amount
    if fine_rule.fine_type == FineType.DAILY:
        effective_days = days_overdue - fine_rule.grace_period_days
        return fine_rule.amount * Decimal(effective_days)
    if fine_rule.fine_type == FineType.SLAB and fine_rule.slab_config:
        for slab in fine_rule.slab_config:
            min_d = slab.get("min_days", 1)
            max_d = slab.get("max_days", 9999)
            if min_d <= days_overdue <= max_d:
                return Decimal(str(slab.get("amount", 0)))
    return Decimal("0.00")


def calculate_invoice_late_fine(
    invoice: Invoice,
    evaluation_date: date | None = None,
    rule: FineRule | None = None,
) -> Decimal:
    """Calculate the late payment fine for an invoice based on its due date and fine rule."""
    if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.WAIVED]:
        return Decimal("0.00")

    ref_date = evaluation_date or timezone.localdate()
    if ref_date <= invoice.due_date:
        return Decimal("0.00")

    fine_rule = rule or invoice.fine_rule
    if not fine_rule:
        fine_rule = (
            FineRule.objects.filter(
                institution=invoice.institution, is_active=True, is_deleted=False
            )
            .order_by("created_at")
            .first()
        )
    if not fine_rule:
        return Decimal("0.00")

    days_overdue = (ref_date - invoice.due_date).days
    if days_overdue <= fine_rule.grace_period_days:
        return Decimal("0.00")

    fine = _calculate_fine_by_type(fine_rule, days_overdue)
    if fine_rule.max_fine_amount is not None:
        fine = min(fine, fine_rule.max_fine_amount)

    return fine.quantize(Decimal("0.01"))


def apply_invoice_fine(
    invoice: Invoice,
    evaluation_date: date | None = None,
    rule: FineRule | None = None,
) -> Invoice:
    """Evaluate and update late fine on an invoice."""
    new_fine = calculate_invoice_late_fine(invoice, evaluation_date=evaluation_date, rule=rule)

    if new_fine != invoice.fine_amount or (
        invoice.status == InvoiceStatus.ISSUED
        and (evaluation_date or timezone.localdate()) > invoice.due_date
    ):
        invoice.fine_amount = new_fine
        invoice.fine_evaluated_at = timezone.now()
        if invoice.fine_rule is None and rule:
            invoice.fine_rule = rule

        # Recalculate totals
        invoice.total_payable = max(
            Decimal("0.00"),
            invoice.subtotal_amount - invoice.waiver_amount + invoice.fine_amount,
        )
        invoice.due_amount = max(Decimal("0.00"), invoice.total_payable - invoice.paid_amount)

        if (
            invoice.status == InvoiceStatus.ISSUED
            and (evaluation_date or timezone.localdate()) > invoice.due_date
        ):
            invoice.status = InvoiceStatus.OVERDUE

        invoice.save(
            update_fields=[
                "fine_amount",
                "fine_rule",
                "fine_evaluated_at",
                "total_payable",
                "due_amount",
                "status",
                "updated_at",
            ]
        )

    return invoice


def evaluate_overdue_invoices_batch(
    institution_id: UUID | str,
    evaluation_date: date | None = None,
) -> int:
    """Batch job evaluating late fines on all pending overdue invoices for an institution."""
    ref_date = evaluation_date or timezone.localdate()
    invoices = Invoice.objects.filter(
        institution_id=institution_id,
        status__in=[InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE],
        due_date__lt=ref_date,
        is_deleted=False,
    ).select_related("fine_rule", "institution")

    count = 0
    with transaction.atomic():
        for inv in invoices:
            apply_invoice_fine(inv, evaluation_date=ref_date)
            count += 1

    return count
