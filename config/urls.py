"""Root URL Configuration for School Management System."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import SpaDashboardView

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # API v1 routes
    path("api/v1/", include("apps.core.urls", namespace="v1_core")),
    path("api/v1/auth/", include("apps.accounts.urls", namespace="v1_accounts")),
    path("api/v1/institutions/", include("apps.institutions.urls", namespace="v1_institutions")),
    path("api/v1/academics/", include("apps.academics.urls", namespace="v1_academics")),
    path("api/v1/admissions/", include("apps.admissions.urls", namespace="v1_admissions")),
    path("api/v1/students/", include("apps.students.urls", namespace="v1_students")),
    path("api/v1/guardians/", include("apps.guardians.urls", namespace="v1_guardians")),
    path("api/v1/staff/", include("apps.staff.urls", namespace="v1_staff")),
    path("api/v1/devices/", include("apps.devices.urls", namespace="v1_devices")),
    path("api/v1/attendance/", include("apps.attendance.urls", namespace="v1_attendance")),
    path("api/v1/exams/", include("apps.exams.urls", namespace="v1_exams")),
    path("api/v1/results/", include("apps.results.urls", namespace="v1_results")),
    path("api/v1/fees/", include("apps.fees.urls", namespace="v1_fees")),
    path(
        "api/v1/communications/", include("apps.communications.urls", namespace="v1_communications")
    ),
    path("api/v1/accounting/", include("apps.accounting.urls", namespace="v1_accounting")),
    path("api/v1/payroll/", include("apps.payroll.urls", namespace="v1_payroll")),
    path("api/v1/homework/", include("apps.homework.urls", namespace="v1_homework")),
    path("api/v1/library/", include("apps.library.urls", namespace="v1_library")),
    path("api/v1/transport/", include("apps.transport.urls", namespace="v1_transport")),
    # Direct root-level routes for physical ZKTeco ADMS hardware terminals
    path("iclock/", include("apps.devices.urls_adms")),
    # OpenAPI Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # React Dashboard SPA shell catch-all
    path("dashboard/", SpaDashboardView.as_view(), name="dashboard_root"),
    re_path(r"^dashboard/(?:.*)/?$", SpaDashboardView.as_view(), name="dashboard_spa"),
]

# Development-only documentation and debug routes
if settings.DEBUG:
    urlpatterns += [
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
    # Django Debug Toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
