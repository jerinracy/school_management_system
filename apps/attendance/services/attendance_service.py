"""High-level Attendance orchestration: policy resolution, daily recalculation, and absentee marking."""

import logging
from datetime import date, time, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import (
    AttendanceCorrection,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceStatus,
    CorrectionStatus,
    DailyAttendance,
    PolicyAssignment,
)
from apps.attendance.services.rule_engine import evaluate_daily_status
from apps.institutions.models import Holiday, Institution
from apps.staff.models import LeaveRequest, Staff
from apps.students.models import Student

logger = logging.getLogger(__name__)


def resolve_effective_policy(
    institution: Institution,
    user_type: str,
    target_date: date,
    branch: Any = None,
    shift: Any = None,
    class_level: Any = None,
    section: Any = None,
) -> AttendancePolicy:
    """Resolve the highest priority active policy matching institutional criteria."""
    # 1. Check scoped PolicyAssignments
    assignments = (
        PolicyAssignment.objects.filter(
            institution=institution,
            policy__is_active=True,
            policy__is_deleted=False,
            policy__effective_from__lte=target_date,
        )
        .filter(user_type__in=[user_type, "all"])
        .select_related("policy")
        .order_by("-priority", "-created_at")
    )

    for assign in assignments:
        pol = assign.policy
        if pol.effective_to and pol.effective_to < target_date:
            continue

        # Match scoping criteria if specified on assignment
        if assign.branch and assign.branch != branch:
            continue
        if assign.shift and assign.shift != shift:
            continue
        if assign.class_level and assign.class_level != class_level:
            continue
        if assign.section and assign.section != section:
            continue

        return pol

    # 2. Check direct policies on institution
    direct_policy = (
        AttendancePolicy.objects.filter(
            institution=institution,
            is_active=True,
            is_deleted=False,
            user_type__in=[user_type, "all"],
            effective_from__lte=target_date,
        )
        .filter(models_Q_effective_to(target_date))
        .order_by("-version", "-created_at")
        .first()
    )

    if direct_policy:
        return direct_policy

    # 3. Create default fallback policy if none exists
    fallback, _ = AttendancePolicy.objects.get_or_create(
        institution=institution,
        name=f"Standard {user_type.capitalize()} Policy",
        user_type=user_type,
        defaults={
            "start_time": time(8, 0),
            "end_time": time(14, 0),
            "grace_minutes": 15,
            "late_threshold_minutes": 45,
            "half_day_threshold_minutes": 120,
            "early_leave_threshold_minutes": 30,
            "effective_from": date(2020, 1, 1),
        },
    )
    return fallback


def models_Q_effective_to(target_date: date) -> Any:
    from django.db.models import Q

    return Q(effective_to__isnull=True) | Q(effective_to__gte=target_date)


def update_daily_attendance_for_person(
    institution: Institution,
    user_type: str,
    person_id: Any,
    target_date: date,
    force_override: bool = False,
) -> DailyAttendance | None:
    """Calculate and upsert DailyAttendance record for a specific student or staff on a date."""
    student: Student | None = None
    staff: Staff | None = None
    branch = None
    shift = None
    class_level = None
    section = None

    if user_type == "student":
        try:
            student = Student.objects.get(id=person_id, institution=institution, is_deleted=False)
        except Student.DoesNotExist:
            return None

        # Fetch active enrollment for branch/shift/section resolution
        enrollment = (
            student.enrollments.filter(is_deleted=False)
            .select_related("shift__branch", "class_level", "section")
            .order_by("-created_at")
            .first()
        )

        if enrollment:
            shift = enrollment.shift
            branch = shift.branch if shift else None
            class_level = enrollment.class_level
            section = enrollment.section

    elif user_type == "staff":
        try:
            staff = Staff.objects.get(id=person_id, institution=institution, is_deleted=False)
        except Staff.DoesNotExist:
            return None

    policy = resolve_effective_policy(
        institution=institution,
        user_type=user_type,
        target_date=target_date,
        branch=branch,
        shift=shift,
        class_level=class_level,
        section=section,
    )

    # Check institutional calendar
    is_weekend = target_date.weekday() in policy.weekend_days
    is_holiday = Holiday.objects.filter(
        institution=institution,
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).exists()

    # Check approved leave
    has_approved_leave = False
    if staff:
        has_approved_leave = LeaveRequest.objects.filter(
            staff=staff,
            status="approved",
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).exists()

    # Query events on target_date
    events_qs = AttendanceEvent.objects.filter(
        institution=institution,
        timestamp__date=target_date,
    )
    if student:
        events = list(events_qs.filter(student=student).order_by("timestamp"))
    else:
        events = list(events_qs.filter(staff=staff).order_by("timestamp"))

    eval_result = evaluate_daily_status(
        events=events,
        policy=policy,
        target_date=target_date,
        is_holiday=is_holiday,
        is_weekend=is_weekend,
        has_approved_leave=has_approved_leave,
    )

    with transaction.atomic():
        daily_record, _ = DailyAttendance.objects.get_or_create(
            institution=institution,
            student=student,
            staff=staff,
            date=target_date,
            defaults={
                "user_type": user_type,
                "status": eval_result.status,
                "first_in": eval_result.first_in,
                "last_out": eval_result.last_out,
                "total_minutes": eval_result.total_minutes,
                "minutes_late": eval_result.minutes_late,
                "minutes_early_leave": eval_result.minutes_early_leave,
                "policy": policy,
                "policy_version": policy.version,
                "remarks": eval_result.remarks,
            },
        )

        if not daily_record.is_overridden or force_override:
            daily_record.status = eval_result.status
            daily_record.first_in = eval_result.first_in
            daily_record.last_out = eval_result.last_out
            daily_record.total_minutes = eval_result.total_minutes
            daily_record.minutes_late = eval_result.minutes_late
            daily_record.minutes_early_leave = eval_result.minutes_early_leave
            daily_record.policy = policy
            daily_record.policy_version = policy.version
            if not daily_record.is_overridden:
                daily_record.remarks = eval_result.remarks
            daily_record.save()

    return daily_record


def recompute_daily_attendance(
    institution: Institution,
    start_date: date,
    end_date: date,
    user_type: str = "all",
    student_ids: list[Any] | None = None,
    staff_ids: list[Any] | None = None,
) -> int:
    """Idempotent batch recomputation across a date range."""
    recomputed_count = 0
    curr_date = start_date

    while curr_date <= end_date:
        # Students
        if user_type in ["student", "all"]:
            s_qs = Student.objects.filter(
                institution=institution, status="active", is_deleted=False
            )
            if student_ids:
                s_qs = s_qs.filter(id__in=student_ids)

            for student in s_qs.only("id"):
                rec = update_daily_attendance_for_person(
                    institution=institution,
                    user_type="student",
                    person_id=student.id,
                    target_date=curr_date,
                )
                if rec:
                    recomputed_count += 1

        # Staff
        if user_type in ["staff", "all"]:
            st_qs = Staff.objects.filter(institution=institution, status="active", is_deleted=False)
            if staff_ids:
                st_qs = st_qs.filter(id__in=staff_ids)

            for staff in st_qs.only("id"):
                rec = update_daily_attendance_for_person(
                    institution=institution,
                    user_type="staff",
                    person_id=staff.id,
                    target_date=curr_date,
                )
                if rec:
                    recomputed_count += 1

        curr_date += timedelta(days=1)

    return recomputed_count


def mark_daily_absentees_for_date(
    institution: Institution,
    target_date: date,
    user_type: str = "all",
) -> int:
    """EOD scheduled job: marks absentees/holidays/weekends for individuals who never punched."""
    marked_count = 0

    if user_type in ["student", "all"]:
        active_students = (
            Student.objects.filter(
                institution=institution,
                status="active",
                is_deleted=False,
            )
            .exclude(
                daily_attendances__date=target_date,
                daily_attendances__is_deleted=False,
            )
            .only("id")
        )

        for s in active_students:
            rec = update_daily_attendance_for_person(
                institution=institution,
                user_type="student",
                person_id=s.id,
                target_date=target_date,
            )
            if rec:
                marked_count += 1

    if user_type in ["staff", "all"]:
        active_staff = (
            Staff.objects.filter(
                institution=institution,
                status="active",
                is_deleted=False,
            )
            .exclude(
                daily_attendances__date=target_date,
                daily_attendances__is_deleted=False,
            )
            .only("id")
        )

        for st in active_staff:
            rec = update_daily_attendance_for_person(
                institution=institution,
                user_type="staff",
                person_id=st.id,
                target_date=target_date,
            )
            if rec:
                marked_count += 1

    return marked_count


def submit_manual_attendance(
    institution: Institution,
    target_date: date,
    user_type: str,
    records: list[dict[str, Any]],
    taken_by: Any = None,
) -> list[DailyAttendance]:
    """Bulk manual roll call by teacher or administrator."""
    created_or_updated: list[DailyAttendance] = []

    with transaction.atomic():
        for item in records:
            person_id = item["person_id"]
            stat = item.get("status", AttendanceStatus.PRESENT)
            remarks = item.get("remarks", "Manual entry")

            student = None
            staff = None
            if user_type == "student":
                student = Student.objects.get(id=person_id, institution=institution)
            else:
                staff = Staff.objects.get(id=person_id, institution=institution)

            daily, _ = DailyAttendance.objects.update_or_create(
                institution=institution,
                student=student,
                staff=staff,
                date=target_date,
                defaults={
                    "user_type": user_type,
                    "status": stat,
                    "is_overridden": True,
                    "override_reason": remarks,
                    "overridden_by": taken_by,
                    "remarks": remarks,
                },
            )
            created_or_updated.append(daily)

    return created_or_updated


def request_attendance_correction(
    daily_attendance: DailyAttendance,
    requested_by: Any,
    reason: str,
    status_after: str,
    time_in_after: Any = None,
    time_out_after: Any = None,
) -> AttendanceCorrection:
    """Submit a formal attendance rectification request."""
    return AttendanceCorrection.objects.create(
        institution=daily_attendance.institution,
        daily_attendance=daily_attendance,
        requested_by=requested_by,
        reason=reason,
        status_before=daily_attendance.status,
        status_after=status_after,
        time_in_before=daily_attendance.first_in,
        time_in_after=time_in_after,
        time_out_before=daily_attendance.last_out,
        time_out_after=time_out_after,
        approval_status=CorrectionStatus.PENDING,
    )


def decide_attendance_correction(
    correction: AttendanceCorrection,
    approver: Any,
    approved: bool,
    rejection_reason: str = "",
) -> AttendanceCorrection:
    """Approve or reject an attendance correction request."""
    with transaction.atomic():
        if approved:
            correction.approval_status = CorrectionStatus.APPROVED
            correction.approved_by = approver
            correction.approved_at = timezone.now()

            # Apply changes to DailyAttendance
            daily = correction.daily_attendance
            daily.status = correction.status_after
            if correction.time_in_after:
                daily.first_in = correction.time_in_after
            if correction.time_out_after:
                daily.last_out = correction.time_out_after

            daily.is_overridden = True
            daily.override_reason = f"Correction approved: {correction.reason}"
            daily.overridden_by = approver
            daily.save()
        else:
            correction.approval_status = CorrectionStatus.REJECTED
            correction.approved_by = approver
            correction.approved_at = timezone.now()
            correction.rejection_reason = rejection_reason

        correction.save()

    return correction
