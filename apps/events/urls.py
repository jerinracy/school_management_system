"""URL routing for Events, Unified Calendar, Clubs, Certificates & Gallery."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.events.views import (
    AchievementViewSet,
    AlbumViewSet,
    CertificateViewSet,
    ClubMembershipViewSet,
    ClubViewSet,
    CompetitionResultViewSet,
    CompetitionViewSet,
    EventViewSet,
    GalleryMediaViewSet,
    NoticeReadReceiptViewSet,
    UnifiedCalendarView,
)

app_name = "events"

router = DefaultRouter()
router.register(r"notice-receipts", NoticeReadReceiptViewSet, basename="notice-receipt")
router.register(r"events", EventViewSet, basename="event")
router.register(r"clubs", ClubViewSet, basename="club")
router.register(r"club-memberships", ClubMembershipViewSet, basename="club-membership")
router.register(r"competitions", CompetitionViewSet, basename="competition")
router.register(r"competition-results", CompetitionResultViewSet, basename="competition-result")
router.register(r"achievements", AchievementViewSet, basename="achievement")
router.register(r"certificates", CertificateViewSet, basename="certificate")
router.register(r"albums", AlbumViewSet, basename="album")
router.register(r"gallery-media", GalleryMediaViewSet, basename="gallery-media")

urlpatterns = [
    path("calendar/", UnifiedCalendarView.as_view(), name="unified_calendar"),
    path("", include(router.urls)),
]
