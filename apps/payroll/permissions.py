"""RBAC and self-service permissions for Payroll Management."""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission

CanViewPayroll = HasModulePermission("payroll.view")
CanManagePayroll = HasModulePermission("payroll.manage")
CanApprovePayroll = HasModulePermission("payroll.approve")


class IsPayrollAdminOrSelf(BasePermission):
    """Allow payroll viewers full tenant access, or staff access to their own payslips."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if CanViewPayroll().has_permission(request, view):
            return True
        if hasattr(obj, "staff") and getattr(obj.staff, "user_id", None) == request.user.id:
            return True
        return False
