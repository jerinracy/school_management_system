"""URL routing for Hostel Management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hostel.views import (
    BedViewSet,
    GatePassViewSet,
    HostelAllocationViewSet,
    HostelAttendanceViewSet,
    HostelFeeLinkViewSet,
    HostelViewSet,
    HostelVisitorLogViewSet,
    MealAttendanceViewSet,
    MealPlanViewSet,
    RoomViewSet,
)

app_name = "hostel"

router = DefaultRouter()
router.register("hostels", HostelViewSet, basename="hostel")
router.register("rooms", RoomViewSet, basename="room")
router.register("beds", BedViewSet, basename="bed")
router.register("fee-links", HostelFeeLinkViewSet, basename="fee-link")
router.register("allocations", HostelAllocationViewSet, basename="allocation")
router.register("attendances", HostelAttendanceViewSet, basename="attendance")
router.register("gate-passes", GatePassViewSet, basename="gate-pass")
router.register("meal-plans", MealPlanViewSet, basename="meal-plan")
router.register("meal-attendances", MealAttendanceViewSet, basename="meal-attendance")
router.register("visitors", HostelVisitorLogViewSet, basename="visitor")

urlpatterns = [
    path("", include(router.urls)),
]
