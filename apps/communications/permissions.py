"""Custom permissions for communications module."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsCommunicationsAdmin(BasePermission):
    """Allows full access to institution admins and superusers."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        user_types = getattr(user, "user_types", []) or []
        return bool({"institution_admin", "principal", "headmaster"} & set(user_types))


class IsNoticeAdminOrReadOnly(BasePermission):
    """Read-only for all authenticated users; write access for admins and teachers."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if getattr(user, "is_superuser", False):
            return True
        user_types = getattr(user, "user_types", []) or []
        return bool(
            {"institution_admin", "principal", "headmaster", "teacher", "staff"} & set(user_types)
        )


class IsThreadParticipant(BasePermission):
    """Allows access only to participants (Teacher or Guardian) or institution admins."""

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        user_types = getattr(user, "user_types", []) or []
        if "institution_admin" in user_types:
            return True

        # Check if user is the teacher
        if hasattr(obj, "teacher") and getattr(obj.teacher, "user_id", None) == user.id:
            return True
        # Check if user is the guardian
        if hasattr(obj, "guardian") and getattr(obj.guardian, "user_id", None) == user.id:
            return True
        # If checking a ChatMessage object
        if hasattr(obj, "thread"):
            if getattr(obj.thread.teacher, "user_id", None) == user.id:
                return True
            if getattr(obj.thread.guardian, "user_id", None) == user.id:
                return True

        return False
