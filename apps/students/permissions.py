"""Permissions for Student management."""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import UserType
from apps.accounts.permissions import HasModulePermission
from apps.guardians.permissions import IsGuardianOfStudent

CanViewStudents = HasModulePermission("students.view")
CanManageStudents = HasModulePermission("students.manage")


class CanViewStudentsOrTeacher(BasePermission):
    """Allow view to users with students.view permission, or teachers and guardians."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if CanViewStudents().has_permission(request, view):
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(
                getattr(user, "user_type", None) in (UserType.TEACHER, UserType.STUDENT)
                or hasattr(user, "staff_profile")
                or hasattr(user, "student_profile")
            )
        return False


__all__ = [
    "CanViewStudents",
    "CanViewStudentsOrTeacher",
    "CanManageStudents",
    "IsGuardianOfStudent",
]
