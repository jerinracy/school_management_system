"""URL routing for institutions module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicSessionViewSet,
    BranchViewSet,
    HolidayViewSet,
    InstitutionProfileView,
    InstitutionPublicBrandingView,
    ShiftViewSet,
    TermViewSet,
)

app_name = "institutions"

router = DefaultRouter()
router.register(r"branches", BranchViewSet, basename="branch")
router.register(r"shifts", ShiftViewSet, basename="shift")
router.register(r"sessions", AcademicSessionViewSet, basename="session")
router.register(r"terms", TermViewSet, basename="term")
router.register(r"holidays", HolidayViewSet, basename="holiday")

urlpatterns = [
    path("public-branding/", InstitutionPublicBrandingView.as_view(), name="public_branding"),
    path("profile/", InstitutionProfileView.as_view(), name="profile"),
    path("", include(router.urls)),
]
