"""Core DRF permission classes."""

from typing import Any

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.core.middleware import check_admin_security


class AdminSecurityPermission(BasePermission):
    """DRF permission enforcing Admin 2FA and IP allowlist for JWT/API requests."""

    def has_permission(self, request: Request, view: Any) -> bool:
        django_req = getattr(request, "_request", request)
        violation = check_admin_security(django_req, getattr(request, "user", None))
        if violation is not None:
            code, message = violation
            raise PermissionDenied(detail=message, code=code)
        return True


class DenyAll(BasePermission):
    """Denies all requests. Default strict fallback."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return False


class IsSuperAdmin(BasePermission):
    """Allows access only to global platform superusers."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsTenantUser(BasePermission):
    """Allows access only to authenticated users attached to an institution."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "institution_id", None) is not None
                or request.user.is_superuser
            )
        )


class IsSameTenant(BasePermission):
    """Ensures object belongs to the user's institution."""

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        user_institution_id = getattr(request.user, "institution_id", None)
        obj_institution_id = getattr(obj, "institution_id", None)

        if not user_institution_id or not obj_institution_id:
            return False

        return bool(user_institution_id == obj_institution_id)
