"""URL configuration for Results, Grading Engine, Report Cards, and Tabulation API endpoints."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.results.views import (
    CumulativeResultViewSet,
    ExamResultViewSet,
    GradingScaleViewSet,
    PublicResultSearchView,
    ReportCardViewSet,
    ResultAnalyticsViewSet,
    ResultPublicationViewSet,
    StudentOptionalSubjectViewSet,
    SubjectResultViewSet,
    TabulationSheetViewSet,
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
router.register(r"tabulation-sheets", TabulationSheetViewSet, basename="tabulation-sheet")
router.register(r"report-cards", ReportCardViewSet, basename="report-card")
router.register(r"publications", ResultPublicationViewSet, basename="publication")
router.register(r"analytics", ResultAnalyticsViewSet, basename="analytics")

urlpatterns = router.urls + [
    path("public-search/", PublicResultSearchView.as_view(), name="public-result-search"),
]
