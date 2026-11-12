"""Permissions for Accounting, Vouchers, Cashbook and Financial Reports."""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission

CanViewAccounting = HasModulePermission("accounting.view")
CanManageAccounting = HasModulePermission("accounting.manage")
CanPostVouchers = HasModulePermission("accounting.post_voucher")
CanCloseCashbook = HasModulePermission("accounting.close_cashbook")


class IsAccountantOrAdmin(BasePermission):
    """Permission allowing institution accountants, financial managers, or superusers."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        # Check explicit module permission
        if CanManageAccounting().has_permission(request, view):
            return True

        # Staff/Admin user_type or role check
        user_type = getattr(request.user, "user_type", "")
        if user_type in ("admin", "superadmin") or getattr(request.user, "is_staff", False):
            return True

        role = getattr(request.user, "role", "")
        if role in {"admin", "accountant", "principal", "headmaster"}:
            return True

        if request.method in ("GET", "HEAD", "OPTIONS") and (
            CanViewAccounting().has_permission(request, view) or role == "staff"
        ):
            return True

        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return self.has_permission(request, view)
