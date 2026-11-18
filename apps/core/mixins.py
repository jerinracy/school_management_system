"""DRF ViewSet and API View Mixins."""

from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request


def get_request_institution(request: Request) -> Any:
    """Helper to extract and type-narrow the user's institution with superadmin fallback."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication credentials were not provided.")

    institution = getattr(user, "institution", None)
    if institution is not None:
        return institution

    # Check if user has a linked staff profile with an institution
    staff_profile = getattr(user, "staff_profile", None)
    if staff_profile and getattr(staff_profile, "institution", None):
        user.institution = staff_profile.institution
        user.save(update_fields=["institution"])
        return staff_profile.institution

    # Superusers / Superadmins fallback to default school institution
    if getattr(user, "is_superuser", False) or getattr(user, "user_type", "") in (
        "superadmin",
        "super_admin",
    ):
        from apps.institutions.models import Institution

        default_inst = Institution.objects.first()
        if default_inst:
            user.institution = default_inst
            user.save(update_fields=["institution"])
            return default_inst

    raise PermissionDenied("User is not associated with an institution.")


class TenantScopedMixin:
    """Mixin for DRF ViewSets ensuring strict tenant data isolation.

    1. Filters get_queryset() to only return objects belonging to the current user's institution.
    2. Automatically assigns request.user.institution on perform_create().
    """

    def get_queryset(self) -> QuerySet:
        """Filter queryset by user's institution."""
        user = getattr(self.request, "user", None)  # type: ignore[attr-defined]
        queryset = super().get_queryset()  # type: ignore[misc]

        if not user or not user.is_authenticated:
            return queryset.none()

        # Platform superusers can access all data if no specific institution filter is applied
        if getattr(user, "is_superuser", False) and not getattr(user, "institution_id", None):
            return queryset

        institution_id = getattr(user, "institution_id", None)
        if not institution_id:
            return queryset.none()

        return queryset.filter(institution_id=institution_id)

    def perform_create(self, serializer: Any) -> None:
        """Inject tenant context into created instances."""
        institution = get_request_institution(self.request)
        serializer.save(institution=institution)
