"""RBAC & privacy permissions for Events, Clubs, Certificates & Gallery."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User, UserType
from apps.accounts.permissions import HasModulePermission
from apps.guardians.models import StudentGuardian
from apps.students.models import Student

CanViewEvents = HasModulePermission("events.view")
CanManageEvents = HasModulePermission("events.manage")


def has_events_staff_permission(request: Request, view: APIView) -> bool:
    return bool(
        CanViewEvents().has_permission(request, view)
        or CanManageEvents().has_permission(request, view)
    )


def has_events_manage_permission(request: Request, view: APIView) -> bool:
    return bool(CanManageEvents().has_permission(request, view))


def resolve_student_for_user(user: Any) -> Student | None:
    if not isinstance(user, User):
        return None
    stu_profile = getattr(user, "student_profile", None)
    if isinstance(stu_profile, Student) and not stu_profile.is_deleted:
        return stu_profile
    if user.user_type == UserType.STUDENT and user.institution_id:
        return Student.objects.filter(
            institution_id=user.institution_id,
            student_id=user.username,
            is_deleted=False,
        ).first()
    return None


def resolve_guardian_ward_ids(user: Any) -> list[Any]:
    if not isinstance(user, User) or not user.institution_id:
        return []
    return list(
        StudentGuardian.objects.filter(
            institution_id=user.institution_id,
            guardian__user=user,
            guardian__is_deleted=False,
            student__is_deleted=False,
        ).values_list("student_id", flat=True)
    )


class CanReadOrManageEvents(BasePermission):
    """Allow authenticated institution members to read; require events.manage to mutate."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated or not user.institution_id:
            return False
        if request.method in SAFE_METHODS:
            return True
        return has_events_manage_permission(request, view)


class CanManageEventsOnly(BasePermission):
    """Require events.manage for all operations."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated or not user.institution_id:
            return False
        return has_events_manage_permission(request, view)
