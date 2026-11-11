"""Leave management, balance ledger, and approval workflow services."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.institutions.models import AcademicSession, Institution
from apps.staff.models import (
    GenderRestriction,
    LeaveBalance,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
    Staff,
    StaffStatus,
)


def initialize_leave_balances_for_session(
    institution: Institution,
    session: AcademicSession,
) -> int:
    """Instantiate initial annual leave quota records for all active staff in the session."""
    active_staff = Staff.objects.filter(institution=institution, status=StaffStatus.ACTIVE)
    active_leave_types = LeaveType.objects.filter(institution=institution)
    created_count = 0

    with transaction.atomic():
        for staff in active_staff:
            for lt in active_leave_types:
                # Check gender restriction
                if lt.gender_restriction == GenderRestriction.MALE and staff.gender != "male":
                    continue
                if lt.gender_restriction == GenderRestriction.FEMALE and staff.gender != "female":
                    continue

                _, created = LeaveBalance.objects.get_or_create(
                    institution=institution,
                    staff=staff,
                    leave_type=lt,
                    session=session,
                    defaults={
                        "allocated_days": Decimal(str(lt.yearly_quota)),
                        "carried_forward_days": Decimal("0.0"),
                        "used_days": Decimal("0.0"),
                        "pending_days": Decimal("0.0"),
                    },
                )
                if created:
                    created_count += 1

    return created_count


def validate_no_leave_overlap(
    staff: Staff,
    start_date: Any,
    end_date: Any,
    exclude_request_id: Any = None,
) -> None:
    """Ensure that the requested date range does not collide with an existing active/pending leave."""
    qs = LeaveRequest.objects.filter(
        staff=staff,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exclude(status__in=[LeaveRequestStatus.REJECTED, LeaveRequestStatus.CANCELLED])

    if exclude_request_id:
        qs = qs.exclude(id=exclude_request_id)

    conflict = qs.first()
    if conflict:
        raise ValidationError(
            f"Leave overlaps with existing {conflict.leave_type.code} leave "
            f"from {conflict.start_date} to {conflict.end_date} (Status: {conflict.status})."
        )


def apply_for_leave(
    staff: Staff,
    leave_type: LeaveType,
    session: AcademicSession,
    start_date: Any,
    end_date: Any,
    reason: str,
    emergency_phone: str = "",
    attachment: Any = None,
) -> LeaveRequest:
    """Submit a leave request, validate limits and overlap, and reserve pending days on balance."""
    if start_date > end_date:
        raise ValidationError("Leave start date cannot be later than end date.")

    # Check gender restriction
    if leave_type.gender_restriction == GenderRestriction.MALE and staff.gender != "male":
        raise ValidationError("This leave type is only available for male staff.")
    if leave_type.gender_restriction == GenderRestriction.FEMALE and staff.gender != "female":
        raise ValidationError("This leave type is only available for female staff.")

    days_count = Decimal(str((end_date - start_date).days + 1))
    validate_no_leave_overlap(staff, start_date, end_date)

    with transaction.atomic():
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
            institution=staff.institution,
            staff=staff,
            leave_type=leave_type,
            session=session,
            defaults={"allocated_days": Decimal(str(leave_type.yearly_quota))},
        )

        if balance.remaining_days < days_count:
            raise ValidationError(
                f"Insufficient leave balance for {leave_type.name}. "
                f"Requested: {days_count} days, Remaining: {balance.remaining_days} days."
            )

        balance.pending_days += days_count
        balance.save(update_fields=["pending_days"])

        req = LeaveRequest.objects.create(
            institution=staff.institution,
            staff=staff,
            leave_type=leave_type,
            session=session,
            start_date=start_date,
            end_date=end_date,
            days_count=days_count,
            reason=reason,
            emergency_phone=emergency_phone,
            attachment=attachment,
            status=LeaveRequestStatus.PENDING,
        )

    return req


def recommend_leave(leave_request: LeaveRequest, recommender: Staff) -> LeaveRequest:
    """Forward a pending leave application to next approval stage with HOD recommendation."""
    if leave_request.status != LeaveRequestStatus.PENDING:
        raise ValidationError(f"Cannot recommend leave in '{leave_request.status}' status.")

    leave_request.recommender = recommender
    leave_request.status = LeaveRequestStatus.RECOMMENDED
    leave_request.save(update_fields=["recommender", "status"])
    return leave_request


def approve_leave(leave_request: LeaveRequest, approver: Staff) -> LeaveRequest:
    """Grant final approval to leave request, decrementing pending days and incrementing used days."""
    if leave_request.status not in [LeaveRequestStatus.PENDING, LeaveRequestStatus.RECOMMENDED]:
        raise ValidationError(f"Cannot approve leave in '{leave_request.status}' status.")

    with transaction.atomic():
        balance = LeaveBalance.objects.select_for_update().get(
            staff=leave_request.staff,
            leave_type=leave_request.leave_type,
            session=leave_request.session,
        )
        balance.pending_days -= leave_request.days_count
        balance.used_days += leave_request.days_count
        balance.save(update_fields=["pending_days", "used_days"])

        leave_request.status = LeaveRequestStatus.APPROVED
        leave_request.approver = approver
        leave_request.decided_at = timezone.now()
        leave_request.save(update_fields=["status", "approver", "decided_at"])

    return leave_request


def reject_leave(
    leave_request: LeaveRequest,
    decider: Staff,
    reason: str = "",
) -> LeaveRequest:
    """Decline a leave application, releasing reserved pending days back to available balance."""
    if leave_request.status not in [LeaveRequestStatus.PENDING, LeaveRequestStatus.RECOMMENDED]:
        raise ValidationError(f"Cannot reject leave in '{leave_request.status}' status.")

    with transaction.atomic():
        balance = LeaveBalance.objects.select_for_update().get(
            staff=leave_request.staff,
            leave_type=leave_request.leave_type,
            session=leave_request.session,
        )
        balance.pending_days -= leave_request.days_count
        balance.save(update_fields=["pending_days"])

        leave_request.status = LeaveRequestStatus.REJECTED
        leave_request.approver = decider
        leave_request.rejection_reason = reason
        leave_request.decided_at = timezone.now()
        leave_request.save(update_fields=["status", "approver", "rejection_reason", "decided_at"])

    return leave_request


def cancel_leave(leave_request: LeaveRequest) -> LeaveRequest:
    """Cancel a leave application (pending or approved), restoring days to balance."""
    if leave_request.status in [LeaveRequestStatus.REJECTED, LeaveRequestStatus.CANCELLED]:
        raise ValidationError(f"Leave is already '{leave_request.status}'.")

    with transaction.atomic():
        balance = LeaveBalance.objects.select_for_update().get(
            staff=leave_request.staff,
            leave_type=leave_request.leave_type,
            session=leave_request.session,
        )
        if leave_request.status == LeaveRequestStatus.APPROVED:
            balance.used_days -= leave_request.days_count
            balance.save(update_fields=["used_days"])
        else:
            balance.pending_days -= leave_request.days_count
            balance.save(update_fields=["pending_days"])

        leave_request.status = LeaveRequestStatus.CANCELLED
        leave_request.save(update_fields=["status"])

    return leave_request
