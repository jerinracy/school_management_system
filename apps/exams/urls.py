"""URL routing for examination endpoints."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.exams.views import (
    AdmitCardViewSet,
    ExamEligibilityPolicyViewSet,
    ExamRoutineViewSet,
    ExamSubjectViewSet,
    ExamTypeViewSet,
    ExamViewSet,
    GraceMarkRuleViewSet,
    MarkEntryViewSet,
    ReScrutinyRequestViewSet,
    SeatPlanViewSet,
    StudentExamEligibilityViewSet,
)

app_name = "exams"

router = DefaultRouter()
router.register("types", ExamTypeViewSet, basename="exam-type")
router.register("exams", ExamViewSet, basename="exam")
router.register("subjects", ExamSubjectViewSet, basename="exam-subject")
router.register("routines", ExamRoutineViewSet, basename="exam-routine")
router.register("policies", ExamEligibilityPolicyViewSet, basename="exam-policy")
router.register("eligibilities", StudentExamEligibilityViewSet, basename="exam-eligibility")
router.register("seat-plans", SeatPlanViewSet, basename="exam-seat-plan")
router.register("admit-cards", AdmitCardViewSet, basename="exam-admit-card")
router.register("mark-entries", MarkEntryViewSet, basename="exam-mark-entry")
router.register("rescrutiny", ReScrutinyRequestViewSet, basename="exam-rescrutiny")
router.register("grace-rules", GraceMarkRuleViewSet, basename="exam-grace-rule")

urlpatterns = [
    path("", include(router.urls)),
]
