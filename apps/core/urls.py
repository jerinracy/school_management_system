"""Core app URL routing."""

from django.urls import path

from .views import HealthCheckView, MetricsView

app_name = "core"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path("metrics/", MetricsView.as_view(), name="system_metrics"),
]
