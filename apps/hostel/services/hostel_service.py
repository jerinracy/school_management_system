"""Business services for Hostel Management (Feature Flag, Bed Allocation, GatePass OTP)."""

import hashlib
import hmac
import logging
import secrets
from datetime import date, datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.guardians.models import StudentGuardian
from apps.hostel.models import (
    Bed,
    BedStatus,
    GatePass,
    GatePassStatus,
    Hostel,
    HostelAllocation,
    HostelFeeLink,
)

logger = logging.getLogger(__name__)


def is_hostel_enabled(institution: Any) -> bool:
    """Return True if the Hostel module feature flag is enabled for the institution."""
    if institution is None:
        return False
    settings_dict = getattr(institution, "settings", None) or {}
    if not isinstance(settings_dict, dict):
        return False
    if "hostel_enabled" in settings_dict:
        return bool(settings_dict["hostel_enabled"])
    features = settings_dict.get("features") or {}
    if isinstance(features, dict) and "hostel_enabled" in features:
        return bool(features["hostel_enabled"])
    return False


def _hash_otp(raw_otp: str) -> str:
    return hashlib.sha256(raw_otp.encode("utf-8")).hexdigest()


def _notify_guardians_gatepass(
    *,
    gate_pass: GatePass,
    event_type: str,
    extra_context: dict[str, Any] | None = None,
) -> None:
    try:
        from apps.communications.services.notification_service import dispatch_event_notification

        guardians = StudentGuardian.objects.select_related("guardian", "guardian__user").filter(
            institution_id=gate_pass.institution_id,
            student_id=gate_pass.student_id,
            guardian__is_deleted=False,
            guardian__user__isnull=False,
        )
        users = [sg.guardian.user for sg in guardians if sg.guardian.user is not None]
        if not users:
            return
        ctx: dict[str, Any] = {
            "student_id": gate_pass.student.student_id,
            "student_name": gate_pass.student.name_en,
            "hostel": gate_pass.hostel.name,
            "reason": gate_pass.reason,
            "expected_return_at": gate_pass.expected_return_at.isoformat(),
        }
        if extra_context:
            ctx.update(extra_context)
        dispatch_event_notification(
            institution=gate_pass.institution,
            event_type=event_type,
            recipient_users=users,
            context=ctx,
            source_module="hostel",
            reference_id=gate_pass.id,
        )
    except Exception:
        logger.exception("Failed to dispatch hostel gate pass notification")


@transaction.atomic
def allocate_bed(
    *,
    institution: Any,
    session: Any,
    student: Any,
    bed: Bed,
    hostel_fee_link: HostelFeeLink | None = None,
    allocated_date: date | None = None,
    remarks: str = "",
) -> HostelAllocation:
    """Atomically allocate an available Bed to a Student for an AcademicSession."""
    if student.institution_id != institution.id or student.is_deleted:
        raise ValidationError("Student not found in this institution.")
    if session.institution_id != institution.id:
        raise ValidationError("Academic session belongs to another institution.")

    locked_bed = (
        Bed.objects.select_for_update()
        .select_related("room", "room__hostel")
        .filter(id=bed.id, institution=institution, is_deleted=False)
        .first()
    )
    if locked_bed is None:
        raise ValidationError("Bed not found in this institution.")
    if locked_bed.status != BedStatus.AVAILABLE:
        raise ValidationError(f"Bed is currently '{locked_bed.status}' and cannot be allocated.")
    if HostelAllocation.objects.filter(
        institution=institution,
        bed=locked_bed,
        is_deleted=False,
        is_active=True,
    ).exists():
        raise ValidationError("Bed already has an active allocation.")
    if HostelAllocation.objects.filter(
        institution=institution,
        session=session,
        student=student,
        is_deleted=False,
        is_active=True,
    ).exists():
        raise ValidationError("Student already has an active hostel allocation for this session.")

    allocation = HostelAllocation.objects.create(
        institution=institution,
        session=session,
        student=student,
        hostel=locked_bed.room.hostel,
        room=locked_bed.room,
        bed=locked_bed,
        hostel_fee_link=hostel_fee_link,
        allocated_date=allocated_date or timezone.localdate(),
        is_active=True,
        remarks=remarks,
    )
    locked_bed.status = BedStatus.OCCUPIED
    locked_bed.save(update_fields=["status", "updated_at"])
    return allocation


@transaction.atomic
def vacate_allocation(
    *,
    institution: Any,
    allocation: HostelAllocation,
    vacated_date: date | None = None,
) -> HostelAllocation:
    """Vacate an active HostelAllocation, preserving history and freeing the Bed."""
    locked = (
        HostelAllocation.objects.select_for_update()
        .select_related("bed")
        .get(id=allocation.id, institution=institution)
    )
    if not locked.is_active:
        raise ValidationError("Allocation is already vacated.")

    locked_bed = Bed.objects.select_for_update().get(id=locked.bed_id)
    locked.is_active = False
    locked.vacated_date = vacated_date or timezone.localdate()
    locked.save(update_fields=["is_active", "vacated_date", "updated_at"])

    locked_bed.status = BedStatus.AVAILABLE
    locked_bed.save(update_fields=["status", "updated_at"])
    return locked


@transaction.atomic
def request_gate_pass(
    *,
    institution: Any,
    student: Any,
    hostel: Hostel,
    reason: str,
    expected_out_at: datetime,
    expected_return_at: datetime,
    destination: str = "",
    otp_ttl_minutes: int = 30,
) -> tuple[GatePass, str]:
    """Create a GatePass in PENDING_GUARDIAN_OTP and dispatch 6-digit OTP to guardian."""
    if student.institution_id != institution.id or student.is_deleted:
        raise ValidationError("Student not found in this institution.")
    if hostel.institution_id != institution.id or hostel.is_deleted:
        raise ValidationError("Hostel not found in this institution.")
    if expected_return_at <= expected_out_at:
        raise ValidationError("expected_return_at must be after expected_out_at.")

    allocation = HostelAllocation.objects.filter(
        institution=institution,
        student=student,
        hostel=hostel,
        is_deleted=False,
        is_active=True,
    ).first()
    raw_otp = f"{secrets.randbelow(1000000):06d}"
    gate_pass = GatePass.objects.create(
        institution=institution,
        student=student,
        hostel=hostel,
        allocation=allocation,
        reason=reason,
        destination=destination,
        expected_out_at=expected_out_at,
        expected_return_at=expected_return_at,
        guardian_otp_hash=_hash_otp(raw_otp),
        guardian_otp_expires_at=timezone.now() + timedelta(minutes=otp_ttl_minutes),
        status=GatePassStatus.PENDING_GUARDIAN_OTP,
    )
    _notify_guardians_gatepass(
        gate_pass=gate_pass,
        event_type="hostel_gatepass_otp",
        extra_context={"otp": raw_otp},
    )
    return gate_pass, raw_otp


@transaction.atomic
def confirm_gate_pass_otp(
    *,
    institution: Any,
    gate_pass: GatePass,
    otp: str,
) -> GatePass:
    """Verify guardian OTP and transition GatePass to GUARDIAN_CONFIRMED."""
    locked = GatePass.objects.select_for_update().get(id=gate_pass.id, institution=institution)
    if locked.status != GatePassStatus.PENDING_GUARDIAN_OTP:
        raise ValidationError(f"GatePass is in '{locked.status}' state, cannot confirm OTP.")
    if not locked.guardian_otp_expires_at or timezone.now() > locked.guardian_otp_expires_at:
        raise ValidationError("Guardian OTP has expired.")
    if not hmac.compare_digest(_hash_otp(otp.strip()), locked.guardian_otp_hash):
        raise ValidationError("Invalid guardian OTP.")

    locked.status = GatePassStatus.GUARDIAN_CONFIRMED
    locked.guardian_confirmed_at = timezone.now()
    locked.save(update_fields=["status", "guardian_confirmed_at", "updated_at"])
    return locked


@transaction.atomic
def approve_gate_pass(*, institution: Any, gate_pass: GatePass, actor: Any) -> GatePass:
    """Approve a GUARDIAN_CONFIRMED GatePass."""
    locked = GatePass.objects.select_for_update().get(id=gate_pass.id, institution=institution)
    if locked.status != GatePassStatus.GUARDIAN_CONFIRMED:
        raise ValidationError("GatePass must be confirmed by guardian OTP before approval.")
    locked.status = GatePassStatus.APPROVED
    locked.approved_by = actor if actor and getattr(actor, "is_authenticated", False) else None
    locked.save(update_fields=["status", "approved_by", "updated_at"])
    return locked


@transaction.atomic
def reject_gate_pass(*, institution: Any, gate_pass: GatePass, actor: Any) -> GatePass:
    """Reject a pending or guardian-confirmed GatePass."""
    locked = GatePass.objects.select_for_update().get(id=gate_pass.id, institution=institution)
    if locked.status not in [
        GatePassStatus.PENDING_GUARDIAN_OTP,
        GatePassStatus.GUARDIAN_CONFIRMED,
    ]:
        raise ValidationError(f"Cannot reject GatePass in '{locked.status}' state.")
    locked.status = GatePassStatus.REJECTED
    locked.approved_by = actor if actor and getattr(actor, "is_authenticated", False) else None
    locked.save(update_fields=["status", "approved_by", "updated_at"])
    return locked


@transaction.atomic
def checkout_gate_pass(*, institution: Any, gate_pass: GatePass) -> GatePass:
    """Mark an APPROVED GatePass as CHECKED_OUT."""
    locked = GatePass.objects.select_for_update().get(id=gate_pass.id, institution=institution)
    if locked.status != GatePassStatus.APPROVED:
        raise ValidationError("Only approved gate passes can check out.")
    locked.status = GatePassStatus.CHECKED_OUT
    locked.actual_out_at = timezone.now()
    locked.save(update_fields=["status", "actual_out_at", "updated_at"])
    return locked


@transaction.atomic
def checkin_gate_pass(*, institution: Any, gate_pass: GatePass) -> GatePass:
    """Mark a CHECKED_OUT or OVERDUE GatePass as RETURNED."""
    locked = GatePass.objects.select_for_update().get(id=gate_pass.id, institution=institution)
    if locked.status not in [GatePassStatus.CHECKED_OUT, GatePassStatus.OVERDUE]:
        raise ValidationError("Only checked-out or overdue gate passes can check in.")
    locked.status = GatePassStatus.RETURNED
    locked.actual_return_at = timezone.now()
    locked.save(update_fields=["status", "actual_return_at", "updated_at"])
    return locked
