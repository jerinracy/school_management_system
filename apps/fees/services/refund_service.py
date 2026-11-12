"""Refund lifecycle services for School Management System."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.fees.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentAllocation,
    PaymentStatus,
    Refund,
    RefundStatus,
)
from apps.fees.services.payment_service import debit_student_advance


def request_refund(
    payment: Payment,
    amount: Decimal,
    reason: str,
    requested_by: User,
) -> Refund:
    """Validate and initiate a refund request for a completed payment."""
    if payment.status != PaymentStatus.SUCCESSFUL:
        raise ValidationError("Only successful payments can be refunded.")

    if amount <= Decimal("0.00"):
        raise ValidationError("Refund amount must be strictly greater than 0.")

    existing_refund_sum = payment.refunds.exclude(status=RefundStatus.REJECTED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")
    if existing_refund_sum + amount > payment.amount:
        raise ValidationError(
            f"Requested refund (৳{amount}) exceeds remaining refundable payment balance "
            f"(৳{payment.amount - existing_refund_sum})."
        )

    return Refund.objects.create(
        institution=payment.institution,
        payment=payment,
        student=payment.student,
        amount=amount,
        reason=reason,
        status=RefundStatus.PENDING,
        requested_by=requested_by,
    )


def approve_refund(refund: Refund, approved_by: User) -> Refund:
    """Approve a pending refund request."""
    if refund.status != RefundStatus.PENDING:
        raise ValidationError("Only pending refund requests can be approved.")

    refund.status = RefundStatus.APPROVED
    refund.approved_by = approved_by
    refund.save(update_fields=["status", "approved_by", "updated_at"])
    return refund


def reject_refund(refund: Refund, rejected_by: User, rejection_reason: str) -> Refund:
    """Reject a pending refund request."""
    if refund.status != RefundStatus.PENDING:
        raise ValidationError("Only pending refund requests can be rejected.")

    refund.status = RefundStatus.REJECTED
    refund.rejection_reason = rejection_reason
    refund.approved_by = rejected_by
    refund.save(update_fields=["status", "rejection_reason", "approved_by", "updated_at"])
    return refund


@transaction.atomic
def process_refund(refund: Refund, processed_by: User) -> Refund:
    """Execute an approved refund, reversing invoice allocations and advance balances."""
    refund = Refund.objects.select_for_update().get(id=refund.id)
    if refund.status != RefundStatus.APPROVED:
        raise ValidationError("Only approved refunds can be processed.")

    payment = Payment.objects.select_for_update().get(id=refund.payment_id)
    now = timezone.now()
    remaining_to_unwind = refund.amount

    # 1. Reverse Invoice allocations if applicable
    if payment.invoice_id:
        invoice = (
            Invoice.objects.select_for_update().prefetch_related("lines").get(id=payment.invoice_id)
        )
        # Fetch payment allocations for this payment
        allocations = (
            PaymentAllocation.objects.select_for_update()
            .filter(payment=payment)
            .order_by("-created_at")
        )
        invoice_unwind_amount = Decimal("0.00")

        for alloc in allocations:
            if remaining_to_unwind <= Decimal("0.00"):
                break
            reducible = min(alloc.allocated_amount, remaining_to_unwind)
            alloc.allocated_amount -= reducible
            alloc.save(update_fields=["allocated_amount", "updated_at"])

            # Reverse line item paid_amount
            if alloc.invoice_line_id:
                line = InvoiceLine.objects.select_for_update().get(id=alloc.invoice_line_id)
                line.paid_amount = max(Decimal("0.00"), line.paid_amount - reducible)
                line.save(update_fields=["paid_amount", "updated_at"])

            invoice_unwind_amount += reducible
            remaining_to_unwind -= reducible

        if invoice_unwind_amount > Decimal("0.00"):
            invoice.paid_amount = max(Decimal("0.00"), invoice.paid_amount - invoice_unwind_amount)
            invoice.due_amount = max(Decimal("0.00"), invoice.total_payable - invoice.paid_amount)
            if invoice.paid_amount == Decimal("0.00"):
                invoice.status = InvoiceStatus.ISSUED
                invoice.paid_date = None
            else:
                invoice.status = InvoiceStatus.PARTIALLY_PAID
            invoice.save(
                update_fields=["paid_amount", "due_amount", "status", "paid_date", "updated_at"]
            )

    # 2. If surplus was credited to advance, debit remaining amount from student advance
    if remaining_to_unwind > Decimal("0.00"):
        debit_student_advance(
            student=payment.student,
            amount=remaining_to_unwind,
            invoice=payment.invoice,
            description=f"Refund ৳{refund.amount} for payment {payment.transaction_id}",
        )

    # 3. Mark refund processed
    refund.status = RefundStatus.PROCESSED
    refund.processed_at = now
    refund.save(update_fields=["status", "processed_at", "updated_at"])

    # 4. If payment is fully refunded, update payment status
    total_processed = payment.refunds.filter(status=RefundStatus.PROCESSED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")
    if total_processed >= payment.amount:
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=["status", "updated_at"])

    return refund
