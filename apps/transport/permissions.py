"""RBAC, Driver, and Student/Guardian portal permissions for Transport Management."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User, UserType
from apps.accounts.permissions import HasModulePermission
from apps.guardians.models import StudentGuardian
from apps.students.models import Student
from apps.transport.models import Driver

CanViewTransport = HasModulePermission("transport.view")
CanManageTransport = HasModulePermission("transport.manage")
CanOperateDriverTransport = HasModulePermission("transport.driver")


def has_transport_staff_permission(request: Request, view: APIView) -> bool:
    return bool(
        CanViewTransport().has_permission(request, view)
        or CanManageTransport().has_permission(request, view)
    )


def resolve_driver_for_user(user: Any) -> Driver | None:
    if not isinstance(user, User) or not user.institution_id:
        return None
    return Driver.objects.filter(
        institution_id=user.institution_id,
        staff__user=user,
        is_deleted=False,
    ).first()


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


class CanReadTransportPortal(BasePermission):
    """Allow safe reads to transport staff, drivers, students, and guardians."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if has_transport_staff_permission(
            request, view
        ) or CanOperateDriverTransport().has_permission(request, view):
            return True
        if request.method in SAFE_METHODS:
            return bool(
                user.user_type in (UserType.STUDENT, UserType.GUARDIAN)
                or resolve_driver_for_user(user) is not None
                or resolve_student_for_user(user) is not None
                or resolve_guardian_ward_ids(user)
            )
        return False


class CanOperateTripOrBoarding(BasePermission):
    """Allow transport managers or drivers (with transport.driver or Driver profile) to operate trips/boarding."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return False
        if CanManageTransport().has_permission(
            request, view
        ) or CanOperateDriverTransport().has_permission(request, view):
            return True
        return resolve_driver_for_user(user) is not None
