"""RBAC permissions for Reporting Engine, Dashboard KPIs & Data Exports."""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import HasModulePermission

CanViewReports = HasModulePermission("reports.view")
CanManageReports = HasModulePermission("reports.manage")


def has_reports_view_permission(request: Request, view: APIView) -> bool:
    return bool(
        CanViewReports().has_permission(request, view)
        or CanManageReports().has_permission(request, view)
    )


def has_reports_manage_permission(request: Request, view: APIView) -> bool:
    return bool(CanManageReports().has_permission(request, view))


class CanAccessReports(BasePermission):
    """Allow reports.view/manage for reads; require reports.manage for mutations."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not isinstance(user, User) or not user.is_authenticated or not user.institution_id:
            return False
        if request.method in SAFE_METHODS:
            return has_reports_view_permission(request, view)
        return has_reports_manage_permission(request, view)
