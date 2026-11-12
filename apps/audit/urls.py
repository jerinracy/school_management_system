"""URL routing for Audit Logging & Activity Tracking."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.audit.views import ActivityLogViewSet, AuditLogViewSet

app_name = "audit"

router = DefaultRouter()
router.register(r"logs", AuditLogViewSet, basename="audit-log")
router.register(r"activities", ActivityLogViewSet, basename="activity-log")

urlpatterns = [
    path("", include(router.urls)),
]
