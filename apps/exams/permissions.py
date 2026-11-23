"""Role-based permissions for exam configurations, schedules, and mark entries."""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import UserType
from apps.accounts.permissions import HasModulePermission

CanManageExams = HasModulePermission("exams.manage")
CanLockMarks = HasModulePermission("exams.lock_marks")


class CanViewExams(BasePermission):
    """Allow exam schedule inspection to exam managers, viewers, and teachers."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if HasModulePermission("exams.view")().has_permission(
            request, view
        ) or CanManageExams().has_permission(request, view):
            return True
        return bool(
            getattr(user, "user_type", None) == UserType.TEACHER
            or hasattr(user, "staff_profile")
            or user.user_roles.filter(role__name__icontains="Teacher").exists()
        )


class CanEnterMarks(BasePermission):
    """Allow mark entry to exam controllers, admins, and teachers."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if HasModulePermission("exams.enter_marks")().has_permission(
            request, view
        ) or CanManageExams().has_permission(request, view):
            return True
        return bool(
            getattr(user, "user_type", None) == UserType.TEACHER
            or hasattr(user, "staff_profile")
            or user.user_roles.filter(role__name__icontains="Teacher").exists()
        )
