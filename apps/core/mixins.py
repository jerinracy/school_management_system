"""DRF ViewSet and API View Mixins."""

from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied


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
        user = getattr(self.request, "user", None)  # type: ignore[attr-defined]

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to create resources.")

        institution = getattr(user, "institution", None)
        if not institution and not getattr(user, "is_superuser", False):
            raise PermissionDenied("User does not belong to any institution.")

        if institution:
            serializer.save(institution=institution)
        else:
            serializer.save()
