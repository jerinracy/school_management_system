"""Permission classes for Guardian and Family module."""

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.guardians.models import StudentGuardian

CanViewGuardians = HasModulePermission("guardians.view")
CanManageGuardians = HasModulePermission("guardians.manage")


class IsGuardianOfStudent(permissions.BasePermission):
    """Enforce that a guardian user can only read and manage records belonging to their linked children."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        # Guardian users can only perform object-level read actions on students
        if getattr(view, "action", None) in ["retrieve", "id_card"]:
            return True

        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        student = getattr(obj, "student", obj)

        # Check explicit StudentGuardian link
        has_active_link = StudentGuardian.objects.filter(
            guardian__user=request.user,
            student=student,
        ).exists()

        if has_active_link:
            return True

        # Fallback to phone number match if portal account user has matching phone
        if hasattr(request.user, "phone") and request.user.phone:
            has_phone_link = StudentGuardian.objects.filter(
                guardian__phone=request.user.phone,
                student=student,
            ).exists()
            if has_phone_link:
                return True

            if getattr(student, "emergency_contact_phone", None) == request.user.phone:
                return True

        return False
