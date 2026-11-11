"""Exam eligibility evaluation and admit card issuing service."""

import logging
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.exams.models import (
    AdmitCard,
    ClearanceStatus,
    Exam,
    ExamEligibilityPolicy,
    StudentExamEligibility,
)
from apps.students.models import EnrollmentStatus, StudentEnrollment

logger = logging.getLogger(__name__)


def evaluate_exam_eligibility_for_exam(exam_id: UUID | str) -> list[StudentExamEligibility]:
    """Calculate attendance percentages and evaluate exam eligibility for all participating students.

    Returns:
        List of created or updated StudentExamEligibility records.
    """
    exam = Exam.objects.select_related("session", "institution").get(id=exam_id)
    institution = exam.institution

    # 1. Resolve eligibility policy (exam-specific or default institutional)
    policy = ExamEligibilityPolicy.objects.filter(exam=exam).first()
    if not policy:
        policy = ExamEligibilityPolicy.objects.filter(
            institution=institution,
            exam__isnull=True,
        ).first()

    min_att = policy.min_attendance_percentage if policy else Decimal("75.00")
    non_coll = policy.non_collegiate_threshold if policy else Decimal("60.00")
    allow_non_coll = policy.allow_non_collegiate if policy else True
    require_fees = policy.require_fee_clearance if policy else True

    # 2. Find enrolled students in participating classes
    target_classes = exam.target_classes.all()
    enrollment_qs = StudentEnrollment.objects.filter(
        institution=institution,
        session=exam.session,
        status=EnrollmentStatus.ACTIVE,
        is_deleted=False,
    ).select_related("student", "class_level", "section")

    if target_classes.exists():
        enrollment_qs = enrollment_qs.filter(class_level__in=target_classes)

    students = [e.student for e in enrollment_qs]
    if not students:
        return []

    # 3. Calculate attendance percentage from session start_date to exam start_date
    start_date = exam.session.start_date
    end_date = exam.start_date

    eligibility_records: list[StudentExamEligibility] = []

    for student in students:
        daily_records = DailyAttendance.objects.filter(
            institution=institution,
            student=student,
            date__gte=start_date,
            date__lte=end_date,
        )

        total_working_days = daily_records.exclude(
            status__in=[AttendanceStatus.HOLIDAY, AttendanceStatus.WEEKEND]
        ).count()

        present_days = daily_records.filter(
            status__in=[
                AttendanceStatus.PRESENT,
                AttendanceStatus.LATE,
                AttendanceStatus.HALF_DAY,
            ]
        ).count()

        if total_working_days > 0:
            att_pct = Decimal(str(round((present_days / total_working_days) * 100, 2)))
        else:
            att_pct = Decimal("100.00")  # Default to 100% if no working days recorded yet

        # Dues hook (can be mocked/extended in Task 14 Fees)
        dues_cleared = True

        # Determine clearance status
        if att_pct >= min_att:
            status = ClearanceStatus.ELIGIBLE
            notes = f"Regular eligibility (Attendance: {att_pct}%)"
        elif att_pct >= non_coll and allow_non_coll:
            status = ClearanceStatus.NON_COLLEGIATE
            notes = f"Non-collegiate clearance needed (Attendance: {att_pct}%)"
        else:
            status = ClearanceStatus.DISQUALIFIED
            notes = f"Attendance below threshold (Attendance: {att_pct}%)"

        if require_fees and not dues_cleared:
            status = ClearanceStatus.DISQUALIFIED
            notes += " [Outstanding fee dues]"

        record, _ = StudentExamEligibility.objects.update_or_create(
            institution=institution,
            exam=exam,
            student=student,
            defaults={
                "attendance_percentage": att_pct,
                "dues_cleared": dues_cleared,
                "clearance_status": status,
                "clearance_notes": notes,
            },
        )
        eligibility_records.append(record)

    return eligibility_records


@transaction.atomic
def generate_admit_cards_for_eligible_students(exam_id: UUID | str) -> list[AdmitCard]:
    """Issue AdmitCard records for all eligible / cleared students in an exam."""
    exam = Exam.objects.select_related("institution", "session").get(id=exam_id)
    institution = exam.institution

    # Find students with eligible or non-collegiate or principal-cleared status
    allowed_statuses = [
        ClearanceStatus.ELIGIBLE,
        ClearanceStatus.NON_COLLEGIATE,
        ClearanceStatus.CLEARED_BY_PRINCIPAL,
    ]

    eligible_records = StudentExamEligibility.objects.filter(
        exam=exam,
        clearance_status__in=allowed_statuses,
    ).select_related("student")

    cards: list[AdmitCard] = []
    year = exam.start_date.year

    for idx, elig in enumerate(eligible_records, start=1):
        card_no = f"ADM-{year}-{exam.id.hex[:4].upper()}-{idx:05d}"
        card, _ = AdmitCard.objects.get_or_create(
            institution=institution,
            exam=exam,
            student=elig.student,
            defaults={
                "card_number": card_no,
                "issue_date": timezone.localdate(),
                "is_issued": True,
            },
        )
        cards.append(card)

    return cards
