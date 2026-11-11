"""Permissions for Staff, HR, and Leave management."""

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission

CanViewStaff = HasModulePermission("staff.view")
CanManageStaff = HasModulePermission("staff.manage")
CanApplyLeave = HasModulePermission("leave.apply")
CanApproveLeave = HasModulePermission("leave.approve")


class IsSelfStaff(permissions.BasePermission):
    """Allow staff members to view or modify only their own profile or leave applications."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        # If checking a Staff profile directly
        if hasattr(obj, "user") and obj.user == request.user:
            return True

        # If checking a LeaveRequest or LeaveBalance
        if hasattr(obj, "staff") and obj.staff.user == request.user:
            return True

        return False
