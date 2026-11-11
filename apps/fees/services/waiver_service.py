"""Student waiver resolution and approval lifecycle."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.fees.models import (
    DiscountType,
    FeeHead,
    FeeType,
    StudentWaiver,
    WaiverApprovalStatus,
)
from apps.students.models import Student


def calculate_applicable_waiver(
    student: Student,
    fee_head: FeeHead,
    amount: Decimal,
    billing_date: date | None = None,
) -> Decimal:
    """Calculate the total deductible waiver amount for a student on a specific fee head."""
    if amount <= Decimal("0.00"):
        return Decimal("0.00")

    ref_date = billing_date or timezone.localdate()

    # Query active approved waivers
    waivers = StudentWaiver.objects.filter(
        student=student,
        status=WaiverApprovalStatus.APPROVED,
        is_deleted=False,
    ).prefetch_related("applicable_fee_heads")

    total_waiver = Decimal("0.00")

    for sw in waivers:
        # Date validity check
        if sw.valid_from and ref_date < sw.valid_from:
            continue
        if sw.valid_to and ref_date > sw.valid_to:
            continue

        # Applicable fee heads check
        app_heads = list(sw.applicable_fee_heads.all())
        if app_heads:
            if fee_head not in app_heads:
                continue
        else:
            # Default to Tuition fee if no fee heads explicitly selected
            if fee_head.fee_type != FeeType.TUITION:
                continue

        # Calculate discount
        if sw.discount_type == DiscountType.PERCENTAGE:
            disc = (amount * sw.discount_value) / Decimal("100.00")
            if sw.max_discount_amount is not None:
                disc = min(disc, sw.max_discount_amount)
        else:
            disc = min(amount, sw.discount_value)

        total_waiver += disc

    # Waiver cannot exceed the base fee amount
    return min(amount, total_waiver.quantize(Decimal("0.01")))


def approve_student_waiver(
    waiver_id: UUID | str,
    approver: User,
) -> StudentWaiver:
    """Approve a student waiver."""
    waiver = StudentWaiver.objects.get(id=waiver_id)
    waiver.status = WaiverApprovalStatus.APPROVED
    waiver.approved_by = approver
    waiver.approved_at = timezone.now()
    waiver.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return waiver


def reject_student_waiver(
    waiver_id: UUID | str,
    approver: User,
    reason: str = "",
) -> StudentWaiver:
    """Reject a student waiver."""
    waiver = StudentWaiver.objects.get(id=waiver_id)
    waiver.status = WaiverApprovalStatus.REJECTED
    waiver.approved_by = approver
    waiver.approved_at = timezone.now()
    waiver.rejection_reason = reason
    waiver.save(
        update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"]
    )
    return waiver
