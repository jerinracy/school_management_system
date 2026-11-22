"""RBAC and Student/Guardian portal permissions for Homework & Learning Management."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import UserType
from apps.accounts.permissions import HasModulePermission
from apps.guardians.models import StudentGuardian
from apps.students.models import Student

CanViewHomework = HasModulePermission("homework.view")
CanManageHomework = HasModulePermission("homework.manage")


def resolve_student_for_user(user: Any) -> Student | None:
    """Resolve the active Student profile associated with an authenticated user."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    stu_profile = getattr(user, "student_profile", None)
    if isinstance(stu_profile, Student) and not stu_profile.is_deleted:
        return stu_profile
    if getattr(user, "user_type", None) == UserType.STUDENT and getattr(
        user, "institution_id", None
    ):
        return Student.objects.filter(
            institution_id=user.institution_id,
            student_id=user.username,
            is_deleted=False,
        ).first()
    return None


def resolve_guardian_ward_ids(user: Any) -> list[Any]:
    """Return Student IDs linked to a Guardian portal user within their institution."""
    if not user or not getattr(user, "is_authenticated", False):
        return []
    if not getattr(user, "institution_id", None):
        return []
    return list(
        StudentGuardian.objects.filter(
            institution_id=user.institution_id,
            guardian__user=user,
            guardian__is_deleted=False,
            student__is_deleted=False,
        ).values_list("student_id", flat=True)
    )


def resolve_visible_student_ids(user: Any) -> list[Any]:
    """Return all Student IDs visible to a Student or Guardian user."""
    student = resolve_student_for_user(user)
    if student is not None:
        return [student.id]
    return resolve_guardian_ward_ids(user)


class CanReadLearningContent(BasePermission):
    """Allow safe-method reads to homework staff, students, and guardians only."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if CanViewHomework().has_permission(request, view) or CanManageHomework().has_permission(
            request, view
        ):
            return True
        if request.method in SAFE_METHODS:
            return bool(
                getattr(user, "user_type", None)
                in (UserType.STUDENT, UserType.GUARDIAN, UserType.TEACHER)
                or hasattr(user, "staff_profile")
                or resolve_student_for_user(user) is not None
                or resolve_guardian_ward_ids(user)
            )
        return False


class CanManageHomeworkOrTeacher(BasePermission):
    """Allow homework management to users with homework.manage or teachers."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if CanManageHomework().has_permission(request, view):
            return True
        return bool(
            getattr(user, "user_type", None) == UserType.TEACHER or hasattr(user, "staff_profile")
        )


class CanSubmitHomeworkOrTakeQuiz(BasePermission):
    """Allow students (or homework managers acting on behalf of a student) to submit/attempt."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if CanManageHomework().has_permission(request, view):
            return True
        return resolve_student_for_user(user) is not None
