"""RBAC and member/portal permissions for Library Management."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User, UserType
from apps.accounts.permissions import HasModulePermission
from apps.guardians.models import StudentGuardian
from apps.staff.models import Staff
from apps.students.models import Student

CanViewLibrary = HasModulePermission("library.view")
CanManageLibrary = HasModulePermission("library.manage")
CanIssueLibrary = HasModulePermission("library.issue")


def has_library_staff_permission(request: Request, view: APIView) -> bool:
    """Return True if the user has any library module permission."""
    return bool(
        CanViewLibrary().has_permission(request, view)
        or CanManageLibrary().has_permission(request, view)
        or CanIssueLibrary().has_permission(request, view)
    )


def resolve_student_for_user(user: Any) -> Student | None:
    """Resolve active Student profile for a user."""
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


def resolve_staff_for_user(user: Any) -> Staff | None:
    """Resolve active Staff profile for a user."""
    if not isinstance(user, User):
        return None
    staff_profile = getattr(user, "staff_profile", None)
    if isinstance(staff_profile, Staff) and not staff_profile.is_deleted:
        return staff_profile
    return None


def resolve_guardian_ward_ids(user: Any) -> list[Any]:
    """Return Student IDs linked to a Guardian user within their institution."""
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


class CanReadLibraryPortal(BasePermission):
    """Allow safe reads to library staff and authenticated students/staff/guardians."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if has_library_staff_permission(request, view):
            return True
        if request.method in SAFE_METHODS:
            return bool(
                user.user_type
                in (UserType.STUDENT, UserType.GUARDIAN, UserType.TEACHER, UserType.STAFF)
                or resolve_student_for_user(user) is not None
                or resolve_staff_for_user(user) is not None
                or resolve_guardian_ward_ids(user)
            )
        return False


class CanManageOrIssueLibrary(BasePermission):
    """Allow circulation operations to users with library.manage or library.issue."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            CanManageLibrary().has_permission(request, view)
            or CanIssueLibrary().has_permission(request, view)
        )


class CanReserveLibraryBook(BasePermission):
    """Allow library staff to reserve for any member, and students/staff to reserve for self."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if has_library_staff_permission(request, view):
            return True
        if request.method in SAFE_METHODS:
            return bool(
                resolve_student_for_user(user) is not None
                or resolve_staff_for_user(user) is not None
                or resolve_guardian_ward_ids(user)
            )
        return bool(
            resolve_student_for_user(user) is not None or resolve_staff_for_user(user) is not None
        )
