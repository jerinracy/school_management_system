"""URL routing for admissions app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.admissions.views import (
    AdmissionCircularViewSet,
    AdmissionTestResultViewSet,
    AdmissionTestViewSet,
    ApplicationDocumentViewSet,
    ApplicationPaymentViewSet,
    ApplicationViewSet,
    LotteryDrawViewSet,
    MeritListViewSet,
    PublicAdmitCardView,
    PublicApplicationApplyView,
    PublicApplicationTrackView,
    PublicCircularListView,
    QuotaRuleViewSet,
)

app_name = "admissions"

router = DefaultRouter()
router.register("circulars", AdmissionCircularViewSet, basename="circular")
router.register("quota-rules", QuotaRuleViewSet, basename="quota-rule")
router.register("applications", ApplicationViewSet, basename="application")
router.register("documents", ApplicationDocumentViewSet, basename="document")
router.register("payments", ApplicationPaymentViewSet, basename="payment")
router.register("tests", AdmissionTestViewSet, basename="test")
router.register("results", AdmissionTestResultViewSet, basename="test-result")
router.register("lottery", LotteryDrawViewSet, basename="lottery")
router.register("merit-lists", MeritListViewSet, basename="merit-list")

urlpatterns = [
    # Public Applicant / Guardian Endpoints
    path("public/circulars/", PublicCircularListView.as_view(), name="public-circular-list"),
    path("public/apply/", PublicApplicationApplyView.as_view(), name="public-apply"),
    path("public/track/", PublicApplicationTrackView.as_view(), name="public-track"),
    path(
        "public/<str:application_no>/admit-card/",
        PublicAdmitCardView.as_view(),
        name="public-admit-card",
    ),
    # Admin / Management Endpoints
    path("", include(router.urls)),
]
