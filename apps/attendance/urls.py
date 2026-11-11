"""URL routing for the Attendance application."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.attendance.views import (
    AttendanceCorrectionViewSet,
    AttendanceEventViewSet,
    AttendancePolicyViewSet,
    DailyAttendanceViewSet,
    MobileCheckinViewSet,
    PeriodAttendanceViewSet,
    PolicyAssignmentViewSet,
)

app_name = "attendance"

router = DefaultRouter()
router.register("policies", AttendancePolicyViewSet, basename="policy")
router.register("assignments", PolicyAssignmentViewSet, basename="assignment")
router.register("daily", DailyAttendanceViewSet, basename="daily")
router.register("periods", PeriodAttendanceViewSet, basename="period")
router.register("corrections", AttendanceCorrectionViewSet, basename="correction")
router.register("events", AttendanceEventViewSet, basename="event")
router.register("mobile-checkin", MobileCheckinViewSet, basename="mobile-checkin")

urlpatterns = [
    path("", include(router.urls)),
]
