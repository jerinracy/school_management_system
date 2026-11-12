"""Read-only DRF ViewSets for AuditLog and ActivityLog."""

from datetime import date

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.audit.models import ActivityLog, AuditLog
from apps.audit.permissions import CanViewAudit
from apps.audit.serializers import ActivityLogSerializer, AuditLogSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List immutable audit logs",
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
    ),
    retrieve=extend_schema(summary="Retrieve an immutable audit log entry"),
)
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only, tenant-scoped endpoint for immutable AuditLog entries."""

    queryset = AuditLog.objects.select_related("actor", "institution")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, CanViewAudit]
    filterset_fields = ["action", "module", "target_model", "target_object_id", "actor"]
    search_fields = ["actor_username", "target_repr", "target_object_id", "module"]
    ordering_fields = ["created_at", "action", "module"]

    def get_queryset(self) -> QuerySet[AuditLog]:
        qs = super().get_queryset()
        user = self.request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return qs.none()

        if not (user.is_superuser and not user.institution_id):
            if not user.institution_id:
                return qs.none()
            qs = qs.filter(institution_id=user.institution_id)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        try:
            if date_from:
                qs = qs.filter(created_at__date__gte=date.fromisoformat(date_from))
            if date_to:
                qs = qs.filter(created_at__date__lte=date.fromisoformat(date_to))
        except ValueError as exc:
            raise DRFValidationError({"detail": "Invalid date format. Use YYYY-MM-DD."}) from exc

        return qs


@extend_schema_view(
    list=extend_schema(
        summary="List immutable user activity logs",
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
    ),
    retrieve=extend_schema(summary="Retrieve an immutable user activity log entry"),
)
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only, tenant-scoped endpoint for ActivityLog entries."""

    queryset = ActivityLog.objects.select_related("actor", "institution")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, CanViewAudit]
    filterset_fields = ["activity_type", "module", "actor"]
    search_fields = ["actor_username", "description", "module"]
    ordering_fields = ["created_at", "activity_type", "module"]

    def get_queryset(self) -> QuerySet[ActivityLog]:
        qs = super().get_queryset()
        user = self.request.user
        if not isinstance(user, User) or not user.is_authenticated:
            return qs.none()

        if not (user.is_superuser and not user.institution_id):
            if not user.institution_id:
                return qs.none()
            qs = qs.filter(institution_id=user.institution_id)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        try:
            if date_from:
                qs = qs.filter(created_at__date__gte=date.fromisoformat(date_from))
            if date_to:
                qs = qs.filter(created_at__date__lte=date.fromisoformat(date_to))
        except ValueError as exc:
            raise DRFValidationError({"detail": "Invalid date format. Use YYYY-MM-DD."}) from exc

        return qs
