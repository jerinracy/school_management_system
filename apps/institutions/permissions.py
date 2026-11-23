"""Permission classes for institutions."""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsInstitutionAdminOrReadOnly(BasePermission):
    """Allows read access to authenticated tenant users; write access only to institution admins / superusers."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Read-only access allowed for all authenticated tenant users or superusers
        if request.method in SAFE_METHODS:
            return bool(user.is_superuser or getattr(user, "institution_id", None) is not None)

        # Write access requires superuser or staff/admin in the institution
        if user.is_superuser:
            return True

        # Check if user is staff or has head_teacher/admin/superadmin user_type or permission
        is_staff = getattr(user, "is_staff", False)
        user_type = getattr(user, "user_type", None)
        return is_staff or user_type in ["admin", "head_teacher", "superadmin", "super_admin"]

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        user_institution_id = getattr(user, "institution_id", None)
        obj_institution_id = getattr(obj, "institution_id", getattr(obj, "id", None))

        return bool(user_institution_id and user_institution_id == obj_institution_id)
