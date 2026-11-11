"""Permissions for Fee Management, Invoicing, and Waivers."""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission

CanViewFees = HasModulePermission("fees.view")
CanManageFees = HasModulePermission("fees.manage")
CanGenerateInvoices = HasModulePermission("fees.generate_invoice")
CanApproveWaiver = HasModulePermission("fees.approve_waiver")


class CanViewInvoiceDetail(BasePermission):
    """Allows staff with `fees.view` or the student/guardian whose invoice it is."""

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        # Staff with permission
        if CanViewFees().has_permission(request, view):
            return True

        # Check if student
        stu_profile = getattr(request.user, "student_profile", None)
        if stu_profile and getattr(obj, "student_id", None) == stu_profile.id:
            return True

        # Check if guardian of student
        guardians = (
            list(request.user.guardian_profiles.all())
            if hasattr(request.user, "guardian_profiles")
            else []
        )
        for g in guardians:
            if (
                hasattr(g, "students")
                and g.students.filter(id=getattr(obj, "student_id", None)).exists()
            ):
                return True

        return False
