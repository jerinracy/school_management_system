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
    """Allows access only to participants (Teacher, Guardian, or Student) or institution admins."""

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False) or "institution_admin" in (
            getattr(user, "user_types", []) or []
        ):
            return True

        target = obj.thread if hasattr(obj, "thread") else obj
        participant_ids = {
            getattr(getattr(target, "teacher", None), "user_id", None),
            getattr(getattr(target, "guardian", None), "user_id", None),
            getattr(getattr(target, "student", None), "user_id", None),
        }
        if user.id in participant_ids:
            return True

        # Fallback check for student user by phone or profile linkage
        if target.student and (
            target.student.user_id == user.id
            or (target.student.phone and target.student.phone == getattr(user, "phone", None))
        ):
            if target.student.user_id is None:
                target.student.user = user
                target.student.save(update_fields=["user"])
            return True

        # Fallback check for guardian user by phone or guardian_profiles
        if target.guardian and (
            target.guardian.user_id == user.id
            or (target.guardian.phone and target.guardian.phone == getattr(user, "phone", None))
            or (
                hasattr(user, "guardian_profiles")
                and user.guardian_profiles.filter(id=target.guardian_id).exists()
            )
        ):
            if target.guardian.user_id is None:
                target.guardian.user = user
                target.guardian.save(update_fields=["user"])
            return True

        return False
