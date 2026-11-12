"""URL routing for Homework, Submissions, Syllabus, Lesson Plans, Materials, Online Classes & Quizzes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.homework.views import (
    HomeworkSubmissionViewSet,
    HomeworkViewSet,
    LessonPlanViewSet,
    OnlineClassLinkViewSet,
    QuizOptionViewSet,
    QuizQuestionViewSet,
    QuizViewSet,
    SignedAttachmentDownloadView,
    StudyMaterialViewSet,
    SyllabusTopicViewSet,
)

app_name = "homework"

router = DefaultRouter()
router.register("assignments", HomeworkViewSet, basename="assignment")
router.register("submissions", HomeworkSubmissionViewSet, basename="submission")
router.register("syllabus-topics", SyllabusTopicViewSet, basename="syllabus-topic")
router.register("lesson-plans", LessonPlanViewSet, basename="lesson-plan")
router.register("materials", StudyMaterialViewSet, basename="material")
router.register("online-classes", OnlineClassLinkViewSet, basename="online-class")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("quiz-questions", QuizQuestionViewSet, basename="quiz-question")
router.register("quiz-options", QuizOptionViewSet, basename="quiz-option")

urlpatterns = [
    path("download/", SignedAttachmentDownloadView.as_view(), name="signed-download"),
    path("", include(router.urls)),
]
