"""URL configuration for academics app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics.views import (
    ClassLevelViewSet,
    ClassSubjectViewSet,
    CopySessionView,
    GroupViewSet,
    PeriodViewSet,
    RoomViewSet,
    RoutineSlotViewSet,
    SectionViewSet,
    SubjectViewSet,
    SubstituteAssignmentViewSet,
)

app_name = "academics"

router = DefaultRouter()
router.register("classes", ClassLevelViewSet, basename="class-level")
router.register("groups", GroupViewSet, basename="group")
router.register("sections", SectionViewSet, basename="section")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("class-subjects", ClassSubjectViewSet, basename="class-subject")
router.register("rooms", RoomViewSet, basename="room")
router.register("periods", PeriodViewSet, basename="period")
router.register("routine", RoutineSlotViewSet, basename="routine-slot")
router.register("substitutes", SubstituteAssignmentViewSet, basename="substitute")

urlpatterns = [
    path("copy-session/", CopySessionView.as_view(), name="copy-session"),
    path("", include(router.urls)),
]
