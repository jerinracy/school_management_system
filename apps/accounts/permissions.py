"""Permissions framework: HasModulePermission and require_module_permission."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


def HasModulePermission(permission_codename: str) -> type[BasePermission]:
    """DRF Permission class factory checking user's assigned role permissions or superuser status."""

    class ModulePermission(BasePermission):
        def has_permission(self, request: Request, view: APIView) -> bool:
            user = request.user
            if not user or not user.is_authenticated:
                return False

            if user.is_superuser:
                return True

            if user.has_perm(permission_codename):
                return True

            short_code = permission_codename.split(".")[-1]
            return user.user_roles.filter(role__permissions__codename=short_code).exists()

    return ModulePermission


def require_module_permission(permission_codename: str) -> Callable:
    """View decorator to enforce a specific module permission."""

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped_view(self: Any, request: Request, *args: Any, **kwargs: Any) -> Any:
            user = request.user
            if not user or not user.is_authenticated:
                raise PermissionDenied("Authentication credentials were not provided.")

            if user.is_superuser:
                return view_func(self, request, *args, **kwargs)

            if user.has_perm(permission_codename):
                return view_func(self, request, *args, **kwargs)

            short_code = permission_codename.split(".")[-1]
            has_role_perm = user.user_roles.filter(role__permissions__codename=short_code).exists()

            if not has_role_perm:
                raise PermissionDenied(
                    f"You do not possess the required permission: '{permission_codename}'."
                )

            return view_func(self, request, *args, **kwargs)

        return _wrapped_view

    return decorator
