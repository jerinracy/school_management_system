"""Feature-flag gate, RBAC, and Student/Guardian permissions for Hostel Management."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User, UserType
from apps.accounts.permissions import HasModulePermission
from apps.guardians.models import StudentGuardian
from apps.hostel.services.hostel_service import is_hostel_enabled
from apps.students.models import Student

CanViewHostel = HasModulePermission("hostel.view")
CanManageHostel = HasModulePermission("hostel.manage")
CanWardenHostel = HasModulePermission("hostel.warden")


def has_hostel_staff_permission(request: Request, view: APIView) -> bool:
    return bool(
        CanViewHostel().has_permission(request, view)
        or CanManageHostel().has_permission(request, view)
        or CanWardenHostel().has_permission(request, view)
    )


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


class IsHostelFeatureEnabled(BasePermission):
    """Block all hostel endpoints (403) unless hostel_enabled is True for the institution."""

    message = "Hostel module is not enabled for this institution."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return is_hostel_enabled(user.institution)


class CanReadHostelPortal(BasePermission):
    """Allow safe reads to hostel staff and authenticated students/guardians."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if has_hostel_staff_permission(request, view):
            return True
        if request.method in SAFE_METHODS:
            return bool(
                user.user_type in (UserType.STUDENT, UserType.GUARDIAN)
                or resolve_student_for_user(user) is not None
                or resolve_guardian_ward_ids(user)
            )
        return False


class CanManageOrWardenHostel(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            CanManageHostel().has_permission(request, view)
            or CanWardenHostel().has_permission(request, view)
        )


class CanAccessGatePass(BasePermission):
    """Hostel staff can manage; students/guardians can view and submit/confirm OTP for own/ward passes."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if has_hostel_staff_permission(request, view):
            return True
        return bool(resolve_student_for_user(user) is not None or resolve_guardian_ward_ids(user))
