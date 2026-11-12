"""Core views including system health check."""

import logging
from typing import Any

from django.conf import settings
from django.db import connection
from django.views.generic import TemplateView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from redis import Redis
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import AdminSecurityPermission

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """System health check endpoint verifying database and Redis connectivity."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="System Health Check",
        description="Verifies database and Redis cache connectivity.",
        responses={
            200: OpenApiResponse(description="All backend systems are operational."),
            503: OpenApiResponse(description="One or more dependent systems are degraded."),
        },
        auth=[],
        tags=["System"],
    )
    def get(self, request: Request) -> Response:
        checks: dict[str, Any] = {
            "status": "ok",
            "database": "unknown",
            "redis": "unknown",
            "version": "1.0.0",
        }
        all_healthy = True

        # Database Check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            checks["database"] = "connected"
        except Exception as exc:  # noqa: BLE001
            logger.error("Health check database error: %s", exc)
            checks["database"] = f"error: {str(exc)}"
            all_healthy = False

        # Redis Check
        try:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            client: Redis = Redis.from_url(redis_url, socket_connect_timeout=2)
            if client.ping():
                checks["redis"] = "connected"
            else:
                checks["redis"] = "ping_failed"
                all_healthy = False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Health check Redis error: %s", exc)
            checks["redis"] = f"error: {str(exc)}"
            # Don't fail entire health check if redis is down in local dev without docker
            # but mark degraded
            checks["status"] = "degraded"

        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        if checks["status"] == "degraded" and checks["database"] == "connected":
            status_code = status.HTTP_200_OK

        return Response(checks, status=status_code)


class MetricsView(APIView):
    """Operational metrics endpoint for platform admins & monitoring probes."""

    permission_classes = [IsAuthenticated, IsAdminUser, AdminSecurityPermission]

    @extend_schema(
        summary="System Operational Metrics",
        responses={200: OpenApiTypes.OBJECT},
        tags=["System"],
    )
    def get(self, request: Request) -> Response:
        from apps.accounts.models import User
        from apps.institutions.models import Institution

        return Response(
            {
                "active_institutions": Institution.objects.filter(is_active=True).count(),
                "active_users": User.objects.filter(is_active=True).count(),
                "debug": bool(settings.DEBUG),
                "enforce_admin_2fa": bool(getattr(settings, "ENFORCE_ADMIN_2FA", False)),
            },
            status=status.HTTP_200_OK,
        )


class SpaDashboardView(TemplateView):
    """Serves the single page application shell for the React admin dashboard."""

    template_name = "spa_shell.html"
