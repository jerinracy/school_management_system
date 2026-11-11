"""Permissions for Student management."""

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission

CanViewStudents = HasModulePermission("students.view")
CanManageStudents = HasModulePermission("students.manage")


class IsGuardianOfStudent(permissions.BasePermission):
    """Restrict access for guardian role to only their linked wards."""

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True

        student = getattr(obj, "student", obj)
        if hasattr(request.user, "phone") and request.user.phone:
            if student.emergency_contact_phone == request.user.phone:
                return True
        return False
