"""Result approval and publication lifecycle management service."""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.exams.models import Exam
from apps.results.models import ExamResult, ExamResultStatus, ResultPublication


@transaction.atomic
def approve_exam_results(exam_id: UUID | str, user: User | None = None) -> dict[str, Any]:
    """Approve draft results for an examination (e.g. by Head Teacher / Principal)."""
    exam = Exam.objects.select_related("institution").get(id=exam_id)

    total_results = ExamResult.objects.filter(exam=exam, is_deleted=False)
    if not total_results.exists():
        raise ValidationError("Cannot approve results: No tabulated results found for this exam.")

    total_results.update(status=ExamResultStatus.APPROVED, updated_at=timezone.now())

    pub, _ = ResultPublication.objects.get_or_create(
        institution=exam.institution,
        exam=exam,
    )

    return {
        "status": "approved",
        "exam_id": str(exam.id),
        "exam_name": exam.name,
        "results_approved": total_results.count(),
        "approved_by": str(user.id) if user else None,
    }


@transaction.atomic
def publish_exam_results(
    exam_id: UUID | str,
    user: User | None = None,
    is_visible_to_guardians: bool = True,
    is_visible_to_students: bool = True,
    allow_public_search: bool = False,
    remarks: str = "",
) -> dict[str, Any]:
    """Formally publish examination results to student/guardian portals."""
    exam = Exam.objects.select_related("institution").get(id=exam_id)

    total_results = ExamResult.objects.filter(exam=exam, is_deleted=False)
    if not total_results.exists():
        raise ValidationError("Cannot publish results: No tabulated results found for this exam.")

    # Update ExamResult statuses to PUBLISHED
    total_results.update(status=ExamResultStatus.PUBLISHED, updated_at=timezone.now())

    # Transition Exam model status to published
    exam.status = "published"
    exam.save(update_fields=["status", "updated_at"])

    # Update or create ResultPublication record
    pub, _ = ResultPublication.objects.get_or_create(
        institution=exam.institution,
        exam=exam,
    )
    pub.is_published = True
    pub.published_at = timezone.now()
    pub.is_visible_to_guardians = is_visible_to_guardians
    pub.is_visible_to_students = is_visible_to_students
    pub.allow_public_search = allow_public_search
    pub.published_by = user
    pub.remarks = remarks
    pub.save()

    return {
        "status": "published",
        "exam_id": str(exam.id),
        "exam_name": exam.name,
        "results_published": total_results.count(),
        "published_at": pub.published_at.isoformat(),
        "allow_public_search": allow_public_search,
    }


@transaction.atomic
def unpublish_exam_results(exam_id: UUID | str, user: User | None = None) -> dict[str, Any]:
    """Revert examination publication back to draft status for corrections."""
    exam = Exam.objects.select_related("institution").get(id=exam_id)

    ExamResult.objects.filter(exam=exam, is_deleted=False).update(
        status=ExamResultStatus.DRAFT, updated_at=timezone.now()
    )

    exam.status = "tabulating"
    exam.save(update_fields=["status", "updated_at"])

    pub = ResultPublication.objects.filter(institution=exam.institution, exam=exam).first()
    if pub:
        pub.is_published = False
        pub.save(update_fields=["is_published", "updated_at"])

    return {
        "status": "unpublished",
        "exam_id": str(exam.id),
        "exam_name": exam.name,
    }


def _can_staff_view_result(user: User, exam_result: ExamResult, user_roles: set[str]) -> bool:
    """Check if user has elevated administrative or teacher privileges."""
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    if getattr(user, "institution_id", None) != exam_result.institution_id:
        return False
    return any(r in user_roles for r in ["admin", "principal", "head_teacher", "teacher"])


def _can_student_or_guardian_view_result(
    user: User,
    exam_result: ExamResult,
    pub: ResultPublication,
    user_roles: set[str],
) -> bool:
    """Check if student or guardian is authorized to view this published result."""
    if "student" in user_roles:
        if not pub.is_visible_to_students:
            return False
        stu_profile = getattr(user, "student_profile", None)
        if stu_profile:
            return bool(stu_profile.id == exam_result.student_id)
        return bool(user.username == exam_result.student.student_id)

    if "guardian" in user_roles:
        if not pub.is_visible_to_guardians:
            return False
        guardians = list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
        return any(
            hasattr(g, "students") and g.students.filter(id=exam_result.student_id).exists()
            for g in guardians
        )

    return False


def can_view_exam_result(user: User, exam_result: ExamResult) -> bool:
    """Enforce visibility rules for students, guardians, and teachers."""
    if not user or not user.is_authenticated:
        return False

    user_roles = set(user.user_roles.values_list("role__code", flat=True))
    if _can_staff_view_result(user, exam_result, user_roles):
        return True

    pub = ResultPublication.objects.filter(
        institution=exam_result.institution, exam=exam_result.exam
    ).first()
    if not pub or not pub.is_published:
        return False

    return _can_student_or_guardian_view_result(user, exam_result, pub, user_roles)
