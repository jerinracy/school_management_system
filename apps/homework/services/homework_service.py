"""Business logic for Homework publishing, submissions, grading, and due reminders."""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserType
from apps.communications.services.notification_service import dispatch_event_notification
from apps.guardians.models import StudentGuardian
from apps.homework.models import (
    Homework,
    HomeworkAttachment,
    HomeworkStatus,
    HomeworkSubmission,
    SubmissionAttachment,
    SubmissionStatus,
)
from apps.homework.services.storage_service import validate_and_scan_upload
from apps.institutions.models import Institution
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment

logger = logging.getLogger(__name__)


def _resolve_target_users_for_homework(homework: Homework) -> list[User]:
    """Collect active enrolled students and guardian users for a homework target audience."""
    enrollment_qs = StudentEnrollment.objects.filter(
        institution=homework.institution,
        session=homework.session,
        class_level=homework.class_level,
        status=EnrollmentStatus.ACTIVE,
        is_deleted=False,
    ).select_related("student")

    if homework.section_id:
        enrollment_qs = enrollment_qs.filter(section_id=homework.section_id)

    enrollments = list(enrollment_qs)
    if not enrollments:
        return []

    student_ids = [e.student_id for e in enrollments]
    student_codes = [e.student.student_id for e in enrollments]

    users_by_id: dict[Any, User] = {}
    for u in User.objects.filter(
        institution=homework.institution,
        username__in=student_codes,
        user_type=UserType.STUDENT,
        is_active=True,
    ):
        users_by_id[u.id] = u

    for sg in StudentGuardian.objects.filter(
        institution=homework.institution,
        student_id__in=student_ids,
        guardian__user__isnull=False,
        guardian__is_deleted=False,
    ).select_related("guardian__user"):
        g_user = sg.guardian.user
        if g_user and g_user.is_active:
            users_by_id[g_user.id] = g_user

    return list(users_by_id.values())


def _resolve_users_for_student(institution: Institution, student: Student) -> list[User]:
    """Resolve portal user(s) for a specific student and their guardians."""
    users_by_id: dict[Any, User] = {}
    for u in User.objects.filter(
        institution=institution,
        username=student.student_id,
        user_type=UserType.STUDENT,
        is_active=True,
    ):
        users_by_id[u.id] = u

    for sg in StudentGuardian.objects.filter(
        institution=institution,
        student=student,
        guardian__user__isnull=False,
        guardian__is_deleted=False,
    ).select_related("guardian__user"):
        g_user = sg.guardian.user
        if g_user and g_user.is_active:
            users_by_id[g_user.id] = g_user

    return list(users_by_id.values())


def _safe_dispatch_notification(
    institution: Institution,
    event_type: str,
    recipients: list[User],
    context: dict[str, Any],
    reference_id: Any,
) -> None:
    """Dispatch notification without letting downstream provider issues abort homework state changes."""
    if not recipients:
        return
    try:
        dispatch_event_notification(
            institution=institution,
            event_type=event_type,
            recipient_users=recipients,
            context=context,
            source_module="homework",
            reference_id=reference_id,
        )
    except Exception:
        logger.exception(
            "Failed to dispatch %s notification for homework ref %s", event_type, reference_id
        )


@transaction.atomic
def attach_files_to_homework(
    homework: Homework,
    files: list[Any],
    uploaded_by: User | None = None,
) -> list[HomeworkAttachment]:
    """Validate, AV-scan, and attach files to a Homework assignment."""
    created: list[HomeworkAttachment] = []
    for f in files:
        safe_name, size_bytes, content_type, av_status = validate_and_scan_upload(f)
        created.append(
            HomeworkAttachment.objects.create(
                institution=homework.institution,
                homework=homework,
                file=f,
                original_filename=safe_name,
                content_type=content_type,
                file_size_bytes=size_bytes,
                av_scan_status=av_status,
                uploaded_by=uploaded_by,
            )
        )
    return created


@transaction.atomic
def publish_homework(homework: Homework) -> Homework:
    """Publish a DRAFT homework and notify enrolled students and guardians."""
    if homework.status == HomeworkStatus.CLOSED:
        raise ValidationError("Closed homework cannot be re-published.")

    if homework.status == HomeworkStatus.PUBLISHED:
        return homework

    homework.status = HomeworkStatus.PUBLISHED
    homework.published_at = timezone.now()
    homework.save(update_fields=["status", "published_at", "updated_at"])

    recipients = _resolve_target_users_for_homework(homework)
    _safe_dispatch_notification(
        institution=homework.institution,
        event_type="homework_assigned",
        recipients=recipients,
        context={
            "title": f"New Homework: {homework.title}",
            "message": (
                f"{homework.subject.name_en}: {homework.title}. "
                f"Due on {homework.due_at:%Y-%m-%d %H:%M}."
            ),
            "subject": homework.subject.name_en,
            "homework_title": homework.title,
            "due_at": homework.due_at.isoformat(),
        },
        reference_id=homework.id,
    )
    return homework


@transaction.atomic
def close_homework(homework: Homework) -> Homework:
    """Close a Homework assignment to halt new submissions."""
    if homework.status == HomeworkStatus.CLOSED:
        return homework
    homework.status = HomeworkStatus.CLOSED
    homework.save(update_fields=["status", "updated_at"])
    return homework


@transaction.atomic
def submit_homework(
    homework: Homework,
    student: Student,
    text_response: str = "",
    files: list[Any] | None = None,
    uploaded_by: User | None = None,
    now: Any = None,
) -> HomeworkSubmission:
    """Submit or update a student's homework submission enforcing due-date & late rules."""
    if homework.institution_id != student.institution_id:
        raise ValidationError("Student does not belong to the homework institution.")
    if homework.status != HomeworkStatus.PUBLISHED:
        raise ValidationError("Submissions are only accepted for published homework.")

    current_time = now or timezone.now()
    is_late = current_time > homework.due_at
    if is_late:
        if not homework.allow_late_submission:
            raise ValidationError("Due date has passed and late submissions are disabled.")
        if homework.late_submission_cutoff_at and current_time > homework.late_submission_cutoff_at:
            raise ValidationError("Late submission cutoff deadline has passed.")

    uploaded_files = files or []
    if not text_response.strip() and not uploaded_files:
        existing = HomeworkSubmission.objects.filter(
            homework=homework, student=student, is_deleted=False
        ).first()
        if not existing or not existing.attachments.exists():
            raise ValidationError("Provide either a text response or at least one file attachment.")

    scanned_files = [(f, *validate_and_scan_upload(f)) for f in uploaded_files]

    existing_sub = HomeworkSubmission.objects.filter(
        homework=homework, student=student, is_deleted=False
    ).first()
    if existing_sub and existing_sub.status == SubmissionStatus.GRADED:
        raise ValidationError("Graded submissions cannot be modified.")

    target_status = SubmissionStatus.LATE if is_late else SubmissionStatus.SUBMITTED
    submission, _ = HomeworkSubmission.objects.update_or_create(
        institution=homework.institution,
        homework=homework,
        student=student,
        is_deleted=False,
        defaults={
            "text_response": text_response,
            "submitted_at": current_time,
            "is_late": is_late,
            "status": target_status,
        },
    )

    for f, safe_name, size_bytes, content_type, av_status in scanned_files:
        SubmissionAttachment.objects.create(
            institution=homework.institution,
            submission=submission,
            file=f,
            original_filename=safe_name,
            content_type=content_type,
            file_size_bytes=size_bytes,
            av_scan_status=av_status,
            uploaded_by=uploaded_by,
        )

    return submission


@transaction.atomic
def grade_submission(
    submission: HomeworkSubmission,
    marks_obtained: Decimal,
    feedback: str = "",
    status: str = SubmissionStatus.GRADED,
    graded_by: User | None = None,
) -> HomeworkSubmission:
    """Evaluate a student's homework submission and notify student/guardians."""
    if marks_obtained < Decimal("0.00"):
        raise ValidationError("Marks obtained cannot be negative.")
    if marks_obtained > submission.homework.max_marks:
        raise ValidationError(
            f"Marks obtained ({marks_obtained}) cannot exceed max marks ({submission.homework.max_marks})."
        )
    if status not in (SubmissionStatus.GRADED, SubmissionStatus.RETURNED):
        raise ValidationError("Evaluation status must be 'graded' or 'returned'.")

    submission.marks_obtained = marks_obtained
    submission.feedback = feedback
    submission.status = status
    submission.graded_by = graded_by
    submission.graded_at = timezone.now()
    submission.save(
        update_fields=[
            "marks_obtained",
            "feedback",
            "status",
            "graded_by",
            "graded_at",
            "updated_at",
        ]
    )

    recipients = _resolve_users_for_student(submission.institution, submission.student)
    _safe_dispatch_notification(
        institution=submission.institution,
        event_type="homework_graded",
        recipients=recipients,
        context={
            "title": f"Homework Evaluated: {submission.homework.title}",
            "message": (
                f"{submission.homework.title}: {marks_obtained}/{submission.homework.max_marks}. "
                f"Status: {submission.get_status_display()}."
            ),
            "homework_title": submission.homework.title,
            "marks_obtained": str(marks_obtained),
            "max_marks": str(submission.homework.max_marks),
        },
        reference_id=submission.id,
    )
    return submission


@transaction.atomic
def send_due_soon_reminders(
    institution: Institution | None = None,
    hours_ahead: int = 24,
) -> int:
    """Dispatch idempotent reminders for published homework due within `hours_ahead`."""
    now = timezone.now()
    horizon = now + timedelta(hours=hours_ahead)

    qs = Homework.objects.filter(
        status=HomeworkStatus.PUBLISHED,
        is_deleted=False,
        due_at__gt=now,
        due_at__lte=horizon,
        due_reminder_sent_at__isnull=True,
    ).select_related("institution", "subject", "class_level", "section")

    if institution is not None:
        qs = qs.filter(institution=institution)

    sent_count = 0
    for hw in qs:
        recipients = _resolve_target_users_for_homework(hw)
        _safe_dispatch_notification(
            institution=hw.institution,
            event_type="homework_due_soon",
            recipients=recipients,
            context={
                "title": f"Homework Due Soon: {hw.title}",
                "message": (
                    f"Reminder: '{hw.title}' ({hw.subject.name_en}) is due on "
                    f"{hw.due_at:%Y-%m-%d %H:%M}."
                ),
                "homework_title": hw.title,
                "due_at": hw.due_at.isoformat(),
            },
            reference_id=hw.id,
        )
        hw.due_reminder_sent_at = now
        hw.save(update_fields=["due_reminder_sent_at", "updated_at"])
        sent_count += 1

    return sent_count
