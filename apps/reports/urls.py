"""URL routing for Reporting Engine, Dashboard KPIs & Data Exports."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.reports.views import (
    BulkImportJobViewSet,
    DashboardKPIView,
    ReportDefinitionViewSet,
    ReportExportJobViewSet,
)

app_name = "reports"

router = DefaultRouter()
router.register(r"definitions", ReportDefinitionViewSet, basename="report-definition")
router.register(r"exports", ReportExportJobViewSet, basename="report-export")
router.register(r"imports", BulkImportJobViewSet, basename="bulk-import")

urlpatterns = [
    path("dashboard/kpis/", DashboardKPIView.as_view(), name="dashboard_kpis"),
    path("", include(router.urls)),
]
