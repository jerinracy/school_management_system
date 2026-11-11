"""URL configuration for Results and Grading Engine API endpoints."""

from rest_framework.routers import DefaultRouter

from apps.results.views import (
    CumulativeResultViewSet,
    ExamResultViewSet,
    GradingScaleViewSet,
    StudentOptionalSubjectViewSet,
    SubjectResultViewSet,
    TermWeightageRuleViewSet,
)

app_name = "results"

router = DefaultRouter()
router.register(r"grading-scales", GradingScaleViewSet, basename="grading-scale")
router.register(r"optional-subjects", StudentOptionalSubjectViewSet, basename="optional-subject")
router.register(r"subject-results", SubjectResultViewSet, basename="subject-result")
router.register(r"exam-results", ExamResultViewSet, basename="exam-result")
router.register(r"cumulative-results", CumulativeResultViewSet, basename="cumulative-result")
router.register(r"term-weightages", TermWeightageRuleViewSet, basename="term-weightage")

urlpatterns = router.urls
