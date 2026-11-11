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
