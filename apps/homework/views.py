"""REST API Views for Homework, Submissions, Syllabus, Lesson Plans, Materials, Online Classes & Quizzes."""

from functools import reduce
from operator import or_
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, QuerySet
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserType
from apps.core.mixins import TenantScopedMixin
from apps.homework.models import (
    AVScanStatus,
    Homework,
    HomeworkAttachment,
    HomeworkStatus,
    HomeworkSubmission,
    LessonPlan,
    OnlineClassLink,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    StudyMaterial,
    SubmissionAttachment,
    SyllabusTopic,
)
from apps.homework.permissions import (
    CanManageHomework,
    CanManageHomeworkOrTeacher,
    CanReadLearningContent,
    CanSubmitHomeworkOrTakeQuiz,
    CanViewHomework,
    resolve_student_for_user,
    resolve_visible_student_ids,
)
from apps.homework.serializers import (
    GradeSubmissionInputSerializer,
    HomeworkAttachmentSerializer,
    HomeworkSerializer,
    HomeworkSubmissionSerializer,
    LessonPlanSerializer,
    OnlineClassLinkSerializer,
    QuizAttemptSerializer,
    QuizOptionSerializer,
    QuizQuestionSerializer,
    QuizSerializer,
    StudyMaterialSerializer,
    SubmitHomeworkInputSerializer,
    SubmitQuizAttemptSerializer,
    SyllabusTopicSerializer,
    UpdateSyllabusProgressSerializer,
)
from apps.homework.services import (
    attach_files_to_homework,
    build_attachment_file_response,
    close_homework,
    grade_submission,
    publish_homework,
    recalculate_quiz_total_marks,
    start_quiz_attempt,
    submit_homework,
    submit_quiz_attempt,
    update_syllabus_topic_progress,
    verify_signed_download_token,
)
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment


def _raise_drf_validation(exc: DjangoValidationError) -> None:
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise DRFValidationError(detail)


def _filter_learning_queryset_by_role(
    qs: QuerySet[Any],
    request: Request,
    view: Any,
    published_q: Q | None = None,
) -> QuerySet[Any]:
    """Scope learning resources to staff or enrolled student/guardian class & section."""
    if CanViewHomework().has_permission(request, view) or CanManageHomework().has_permission(
        request, view
    ):
        return qs

    student_ids = resolve_visible_student_ids(request.user)
    if not student_ids:
        return qs.none()

    user = request.user
    inst_id = user.institution_id if isinstance(user, User) else None
    if inst_id is None:
        return qs.none()

    enrollments = list(
        StudentEnrollment.objects.filter(
            institution_id=inst_id,
            student_id__in=student_ids,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        ).values_list("class_level_id", "section_id")
    )
    if not enrollments:
        return qs.none()

    audience_filters = [
        Q(class_level_id=cl_id) & (Q(section__isnull=True) | Q(section_id=sec_id))
        for cl_id, sec_id in enrollments
    ]
    scoped = qs.filter(reduce(or_, audience_filters)).distinct()
    if published_q is not None:
        scoped = scoped.filter(published_q)
    return scoped


def _resolve_target_student(
    request: Request, view: Any, explicit_student_id: Any = None
) -> Student:
    """Resolve submitting/attempting Student cleanly for self-service or staff proxy."""
    student = resolve_student_for_user(request.user)
    if student is not None:
        return student
    user = request.user
    inst_id = user.institution_id if isinstance(user, User) else None
    if explicit_student_id and inst_id and CanManageHomework().has_permission(request, view):
        found = Student.objects.filter(
            id=explicit_student_id,
            institution_id=inst_id,
            is_deleted=False,
        ).first()
        if found:
            return found
    raise DRFValidationError({"student": "No active student profile resolved for this action."})


@extend_schema_view(
    list=extend_schema(summary="List homework assignments", tags=["Homework - Assignments"]),
    retrieve=extend_schema(summary="Retrieve homework details", tags=["Homework - Assignments"]),
    create=extend_schema(summary="Create homework assignment", tags=["Homework - Assignments"]),
    update=extend_schema(summary="Update homework assignment", tags=["Homework - Assignments"]),
    partial_update=extend_schema(
        summary="Partial update homework assignment", tags=["Homework - Assignments"]
    ),
    destroy=extend_schema(summary="Delete homework assignment", tags=["Homework - Assignments"]),
)
class HomeworkViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage homework assignments, attachments, publishing, closing, and submissions."""

    queryset = (
        Homework.objects.filter(is_deleted=False)
        .select_related("session", "class_level", "section", "subject", "teacher")
        .prefetch_related("attachments")
        .order_by("-due_at", "-created_at")
    )
    serializer_class = HomeworkSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["session", "class_level", "section", "subject", "teacher", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_at", "created_at", "max_marks"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action == "submit":
            return [IsAuthenticated(), CanSubmitHomeworkOrTakeQuiz()]
        if self.action in ("list", "retrieve", "submissions"):
            return [IsAuthenticated(), CanReadLearningContent()]
        return [IsAuthenticated(), CanManageHomeworkOrTeacher()]

    def get_queryset(self) -> QuerySet[Homework]:
        qs = super().get_queryset()
        session_id = self.request.query_params.get("session") or self.request.headers.get(
            "X-Academic-Session"
        )
        if session_id and session_id != "all":
            qs = qs.filter(session_id=session_id)
        elif not session_id:
            institution = getattr(self.request.user, "institution", None)
            if institution:
                from apps.institutions.selectors import get_current_academic_session

                curr = get_current_academic_session(institution.id)
                if curr:
                    qs = qs.filter(session_id=curr.id)
        return _filter_learning_queryset_by_role(
            qs,
            self.request,
            self,
            published_q=Q(status__in=[HomeworkStatus.PUBLISHED, HomeworkStatus.CLOSED]),
        )

    @extend_schema(
        summary="Upload file attachment to homework",
        tags=["Homework - Assignments"],
        responses={201: HomeworkAttachmentSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_attachment(self, request: Request, pk: Any = None) -> Response:
        hw = self.get_object()
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not files:
            raise DRFValidationError({"file": "Provide one or more files to attach."})
        user = request.user
        assert isinstance(user, User)
        try:
            created = attach_files_to_homework(hw, list(files), uploaded_by=user)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        ser = HomeworkAttachmentSerializer(created, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Publish homework and trigger notifications",
        tags=["Homework - Assignments"],
        request=None,
        responses={200: HomeworkSerializer},
    )
    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: Any = None) -> Response:
        hw = self.get_object()
        try:
            hw = publish_homework(hw)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(self.get_serializer(hw).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Close homework assignment",
        tags=["Homework - Assignments"],
        request=None,
        responses={200: HomeworkSerializer},
    )
    @action(detail=True, methods=["post"])
    def close(self, request: Request, pk: Any = None) -> Response:
        hw = self.get_object()
        hw = close_homework(hw)
        return Response(self.get_serializer(hw).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit student work (text/files) for homework",
        tags=["Homework - Assignments"],
        request=SubmitHomeworkInputSerializer,
        responses={200: HomeworkSubmissionSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def submit(self, request: Request, pk: Any = None) -> Response:
        hw = self.get_object()
        ser = SubmitHomeworkInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        student = _resolve_target_student(request, self, ser.validated_data.get("student"))
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        user = request.user
        assert isinstance(user, User)
        try:
            sub = submit_homework(
                homework=hw,
                student=student,
                text_response=ser.validated_data.get("text_response", ""),
                files=list(files),
                uploaded_by=user,
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(
            HomeworkSubmissionSerializer(sub, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="List submissions for a homework assignment",
        tags=["Homework - Assignments"],
        responses={200: HomeworkSubmissionSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def submissions(self, request: Request, pk: Any = None) -> Response:
        hw = self.get_object()
        qs = (
            hw.submissions.filter(is_deleted=False)
            .select_related("student", "homework")
            .prefetch_related("attachments")
        )
        if not (
            CanViewHomework().has_permission(request, self)
            or CanManageHomework().has_permission(request, self)
            or getattr(request.user, "user_type", None) == UserType.TEACHER
            or hasattr(request.user, "staff_profile")
        ):
            student_ids = resolve_visible_student_ids(request.user)
            qs = qs.filter(student_id__in=student_ids)
        ser = HomeworkSubmissionSerializer(qs, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List homework submissions", tags=["Homework - Submissions"]),
    retrieve=extend_schema(summary="Retrieve submission details", tags=["Homework - Submissions"]),
)
class HomeworkSubmissionViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """View submissions (teacher/student/guardian scoped) and grade student work."""

    queryset = (
        HomeworkSubmission.objects.filter(is_deleted=False)
        .select_related("homework", "student", "graded_by")
        .prefetch_related("attachments")
        .order_by("-submitted_at")
    )
    serializer_class = HomeworkSubmissionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["homework", "student", "status", "is_late"]
    ordering_fields = ["submitted_at", "marks_obtained"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action == "grade":
            return [IsAuthenticated(), CanManageHomework()]
        return [IsAuthenticated(), CanReadLearningContent()]

    def get_queryset(self) -> QuerySet[HomeworkSubmission]:
        qs = super().get_queryset()
        if (
            CanViewHomework().has_permission(self.request, self)
            or CanManageHomework().has_permission(self.request, self)
            or getattr(self.request.user, "user_type", None) == UserType.TEACHER
            or hasattr(self.request.user, "staff_profile")
        ):
            return qs
        student_ids = resolve_visible_student_ids(self.request.user)
        return qs.filter(student_id__in=student_ids)

    @extend_schema(
        summary="Grade or return a student's homework submission",
        tags=["Homework - Submissions"],
        request=GradeSubmissionInputSerializer,
        responses={200: HomeworkSubmissionSerializer},
    )
    @action(detail=True, methods=["post"])
    def grade(self, request: Request, pk: Any = None) -> Response:
        sub = self.get_object()
        ser = GradeSubmissionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        assert isinstance(user, User)
        try:
            sub = grade_submission(
                submission=sub,
                marks_obtained=ser.validated_data["marks_obtained"],
                feedback=ser.validated_data.get("feedback", ""),
                status=ser.validated_data["status"],
                graded_by=user,
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(
            self.get_serializer(sub, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(summary="List syllabus topics", tags=["Homework - Curriculum"]),
    retrieve=extend_schema(summary="Retrieve syllabus topic", tags=["Homework - Curriculum"]),
    create=extend_schema(summary="Create syllabus topic", tags=["Homework - Curriculum"]),
    update=extend_schema(summary="Update syllabus topic", tags=["Homework - Curriculum"]),
    partial_update=extend_schema(
        summary="Partial update syllabus topic", tags=["Homework - Curriculum"]
    ),
    destroy=extend_schema(summary="Delete syllabus topic", tags=["Homework - Curriculum"]),
)
class SyllabusTopicViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD and progress tracking for curriculum syllabus topics."""

    queryset = (
        SyllabusTopic.objects.filter(is_deleted=False)
        .select_related("session", "term", "class_level", "subject")
        .order_by("class_level", "subject", "order")
    )
    serializer_class = SyllabusTopicSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["session", "term", "class_level", "subject", "status"]
    search_fields = ["title", "title_bn"]
    ordering_fields = ["order", "completion_percentage"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanReadLearningContent()]
        return [IsAuthenticated(), CanManageHomework()]

    @extend_schema(
        summary="Update syllabus topic completion percentage",
        tags=["Homework - Curriculum"],
        request=UpdateSyllabusProgressSerializer,
        responses={200: SyllabusTopicSerializer},
    )
    @action(detail=True, methods=["post"])
    def update_progress(self, request: Request, pk: Any = None) -> Response:
        topic = self.get_object()
        ser = UpdateSyllabusProgressSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            topic = update_syllabus_topic_progress(
                topic, ser.validated_data["completion_percentage"]
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(self.get_serializer(topic).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List lesson plans", tags=["Homework - Curriculum"]),
    retrieve=extend_schema(summary="Retrieve lesson plan", tags=["Homework - Curriculum"]),
    create=extend_schema(summary="Create lesson plan", tags=["Homework - Curriculum"]),
    update=extend_schema(summary="Update lesson plan", tags=["Homework - Curriculum"]),
    partial_update=extend_schema(
        summary="Partial update lesson plan", tags=["Homework - Curriculum"]
    ),
    destroy=extend_schema(summary="Delete lesson plan", tags=["Homework - Curriculum"]),
)
class LessonPlanViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Teacher lesson plan CRUD."""

    queryset = (
        LessonPlan.objects.filter(is_deleted=False)
        .select_related("session", "class_level", "section", "subject", "syllabus_topic", "teacher")
        .order_by("-lesson_date")
    )
    serializer_class = LessonPlanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["session", "class_level", "section", "subject", "teacher", "status"]
    search_fields = ["title", "objectives"]
    ordering_fields = ["lesson_date", "created_at"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewHomework()]
        return [IsAuthenticated(), CanManageHomework()]


@extend_schema_view(
    list=extend_schema(summary="List study materials", tags=["Homework - Materials"]),
    retrieve=extend_schema(summary="Retrieve study material", tags=["Homework - Materials"]),
    create=extend_schema(summary="Upload study material", tags=["Homework - Materials"]),
    update=extend_schema(summary="Update study material", tags=["Homework - Materials"]),
    partial_update=extend_schema(
        summary="Partial update study material", tags=["Homework - Materials"]
    ),
    destroy=extend_schema(summary="Delete study material", tags=["Homework - Materials"]),
)
class StudyMaterialViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Downloadable lecture notes and reference links scoped by class/section."""

    queryset = (
        StudyMaterial.objects.filter(is_deleted=False)
        .select_related("session", "class_level", "section", "subject", "uploaded_by")
        .order_by("-created_at")
    )
    serializer_class = StudyMaterialSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["session", "class_level", "section", "subject", "material_type"]
    search_fields = ["title", "description"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanReadLearningContent()]
        return [IsAuthenticated(), CanManageHomeworkOrTeacher()]

    def perform_create(self, serializer: Any) -> None:
        from apps.core.mixins import get_request_institution

        institution = get_request_institution(self.request)
        serializer.save(
            institution=institution,
            uploaded_by=self.request.user if self.request.user.is_authenticated else None,
        )

    def get_queryset(self) -> QuerySet[StudyMaterial]:
        qs = super().get_queryset()
        session_id = self.request.query_params.get("session") or self.request.headers.get(
            "X-Academic-Session"
        )
        if session_id and session_id != "all":
            qs = qs.filter(session_id=session_id)
        elif not session_id:
            institution = getattr(self.request.user, "institution", None)
            if institution:
                from apps.institutions.selectors import get_current_academic_session

                curr = get_current_academic_session(institution.id)
                if curr:
                    qs = qs.filter(session_id=curr.id)
        return _filter_learning_queryset_by_role(
            qs,
            self.request,
            self,
            published_q=Q(is_published=True),
        )


@extend_schema_view(
    list=extend_schema(summary="List online class links", tags=["Homework - Online Classes"]),
    retrieve=extend_schema(
        summary="Retrieve online class link", tags=["Homework - Online Classes"]
    ),
    create=extend_schema(summary="Schedule online class", tags=["Homework - Online Classes"]),
    update=extend_schema(summary="Update online class", tags=["Homework - Online Classes"]),
    partial_update=extend_schema(
        summary="Partial update online class", tags=["Homework - Online Classes"]
    ),
    destroy=extend_schema(summary="Delete online class", tags=["Homework - Online Classes"]),
)
class OnlineClassLinkViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Scheduled Zoom/Meet links filtered by class and section."""

    queryset = (
        OnlineClassLink.objects.filter(is_deleted=False)
        .select_related("session", "class_level", "section", "subject", "teacher")
        .order_by("-scheduled_start")
    )
    serializer_class = OnlineClassLinkSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["session", "class_level", "section", "subject", "status"]
    search_fields = ["title", "platform"]
    ordering_fields = ["scheduled_start"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanReadLearningContent()]
        return [IsAuthenticated(), CanManageHomework()]

    def get_queryset(self) -> QuerySet[OnlineClassLink]:
        return _filter_learning_queryset_by_role(super().get_queryset(), self.request, self)


@extend_schema_view(
    list=extend_schema(summary="List quizzes", tags=["Homework - Quizzes"]),
    retrieve=extend_schema(summary="Retrieve quiz details", tags=["Homework - Quizzes"]),
    create=extend_schema(summary="Create quiz", tags=["Homework - Quizzes"]),
    update=extend_schema(summary="Update quiz", tags=["Homework - Quizzes"]),
    partial_update=extend_schema(summary="Partial update quiz", tags=["Homework - Quizzes"]),
    destroy=extend_schema(summary="Delete quiz", tags=["Homework - Quizzes"]),
)
class QuizViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Online quiz management plus student attempt & auto-grading endpoints."""

    queryset = (
        Quiz.objects.filter(is_deleted=False)
        .select_related("session", "class_level", "section", "subject", "teacher")
        .prefetch_related("questions__options")
        .order_by("-starts_at")
    )
    serializer_class = QuizSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["session", "class_level", "section", "subject", "is_published"]
    search_fields = ["title", "description"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("start_attempt", "submit_attempt"):
            return [IsAuthenticated(), CanSubmitHomeworkOrTakeQuiz()]
        if self.action in ("list", "retrieve", "my_attempts"):
            return [IsAuthenticated(), CanReadLearningContent()]
        return [IsAuthenticated(), CanManageHomework()]

    def get_queryset(self) -> QuerySet[Quiz]:
        return _filter_learning_queryset_by_role(
            super().get_queryset(),
            self.request,
            self,
            published_q=Q(is_published=True),
        )

    @extend_schema(
        summary="Start or resume a quiz attempt",
        tags=["Homework - Quizzes"],
        request=None,
        responses={200: QuizAttemptSerializer},
    )
    @action(detail=True, methods=["post"])
    def start_attempt(self, request: Request, pk: Any = None) -> Response:
        quiz = self.get_object()
        student = _resolve_target_student(request, self, request.data.get("student"))
        try:
            attempt = start_quiz_attempt(quiz, student)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit answers and auto-grade quiz attempt",
        tags=["Homework - Quizzes"],
        request=SubmitQuizAttemptSerializer,
        responses={200: QuizAttemptSerializer},
    )
    @action(detail=True, methods=["post"])
    def submit_attempt(self, request: Request, pk: Any = None) -> Response:
        quiz = self.get_object()
        ser = SubmitQuizAttemptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        attempt = QuizAttempt.objects.filter(
            id=ser.validated_data["attempt_id"],
            quiz=quiz,
            institution_id=quiz.institution_id,
        ).first()
        if not attempt:
            raise DRFValidationError({"attempt_id": "Quiz attempt not found."})

        if not CanManageHomework().has_permission(request, self):
            student = resolve_student_for_user(request.user)
            if student is None or attempt.student_id != student.id:
                raise PermissionDenied("You may only submit your own quiz attempt.")

        try:
            graded = submit_quiz_attempt(attempt, ser.validated_data["answers"])
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(QuizAttemptSerializer(graded).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List current student's or ward's quiz attempts",
        tags=["Homework - Quizzes"],
        responses={200: QuizAttemptSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def my_attempts(self, request: Request, pk: Any = None) -> Response:
        quiz = self.get_object()
        student_ids = resolve_visible_student_ids(request.user)
        qs = QuizAttempt.objects.filter(quiz=quiz, student_id__in=student_ids).order_by(
            "attempt_number"
        )
        return Response(QuizAttemptSerializer(qs, many=True).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List quiz questions", tags=["Homework - Quizzes"]),
    retrieve=extend_schema(summary="Retrieve quiz question", tags=["Homework - Quizzes"]),
    create=extend_schema(summary="Create quiz question", tags=["Homework - Quizzes"]),
    update=extend_schema(summary="Update quiz question", tags=["Homework - Quizzes"]),
    partial_update=extend_schema(
        summary="Partial update quiz question", tags=["Homework - Quizzes"]
    ),
    destroy=extend_schema(summary="Delete quiz question", tags=["Homework - Quizzes"]),
)
class QuizQuestionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for QuizQuestions, keeping Quiz.total_marks synchronized."""

    queryset = QuizQuestion.objects.select_related("quiz").prefetch_related("options").all()
    serializer_class = QuizQuestionSerializer
    permission_classes = [IsAuthenticated, CanManageHomework]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["quiz"]

    def perform_create(self, serializer: Any) -> None:
        super().perform_create(serializer)
        recalculate_quiz_total_marks(serializer.instance.quiz)

    def perform_update(self, serializer: Any) -> None:
        super().perform_update(serializer)
        recalculate_quiz_total_marks(serializer.instance.quiz)

    def perform_destroy(self, instance: QuizQuestion) -> None:
        quiz = instance.quiz
        instance.delete()
        recalculate_quiz_total_marks(quiz)


@extend_schema_view(
    list=extend_schema(summary="List quiz options", tags=["Homework - Quizzes"]),
    retrieve=extend_schema(summary="Retrieve quiz option", tags=["Homework - Quizzes"]),
    create=extend_schema(summary="Create quiz option", tags=["Homework - Quizzes"]),
    update=extend_schema(summary="Update quiz option", tags=["Homework - Quizzes"]),
    partial_update=extend_schema(summary="Partial update quiz option", tags=["Homework - Quizzes"]),
    destroy=extend_schema(summary="Delete quiz option", tags=["Homework - Quizzes"]),
)
class QuizOptionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for QuizOptions."""

    queryset = QuizOption.objects.select_related("question").all()
    serializer_class = QuizOptionSerializer
    permission_classes = [IsAuthenticated, CanManageHomework]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["question"]


class SignedAttachmentDownloadView(APIView):
    """Serve stored homework, submission, or material files using a verified HMAC token."""

    permission_classes = [IsAuthenticated, CanReadLearningContent]

    @extend_schema(
        summary="Download attachment via signed URL token",
        tags=["Homework - Downloads"],
        parameters=[
            OpenApiParameter(name="token", type=OpenApiTypes.STR, required=True),
        ],
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    def get(self, request: Request) -> FileResponse:
        token = request.query_params.get("token", "")
        if not token:
            raise DRFValidationError({"token": "Signed download token is required."})
        try:
            payload = verify_signed_download_token(token)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)

        user_inst_id = str(getattr(request.user, "institution_id", "") or "")
        if (
            not getattr(request.user, "is_superuser", False)
            and payload["institution_id"] != user_inst_id
        ):
            raise PermissionDenied("Cross-tenant attachment download is forbidden.")

        obj = self._resolve_attachment(
            request, payload["kind"], payload["id"], payload["institution_id"]
        )
        if obj.av_scan_status == AVScanStatus.INFECTED:
            raise PermissionDenied("Attachment quarantined due to malware scan status.")
        filename = obj.original_filename or "download"
        content_type = getattr(obj, "content_type", "application/octet-stream")
        return build_attachment_file_response(obj.file, filename, content_type)

    def _resolve_attachment(
        self, request: Request, kind: str, obj_id: str, inst_id: str
    ) -> HomeworkAttachment | SubmissionAttachment | StudyMaterial:
        if kind == "homework":
            obj = HomeworkAttachment.objects.filter(id=obj_id, institution_id=inst_id).first()
            if not obj:
                raise DRFValidationError("Attachment not found.")
            return obj
        if kind == "material":
            mat = StudyMaterial.objects.filter(
                id=obj_id, institution_id=inst_id, is_deleted=False
            ).first()
            if not mat or not mat.file:
                raise DRFValidationError("Study material file not found.")
            return mat
        if kind == "submission":
            sub_att = (
                SubmissionAttachment.objects.filter(id=obj_id, institution_id=inst_id)
                .select_related("submission")
                .first()
            )
            if not sub_att:
                raise DRFValidationError("Submission attachment not found.")
            if not (
                CanViewHomework().has_permission(request, self)
                or CanManageHomework().has_permission(request, self)
            ):
                allowed_students = resolve_visible_student_ids(request.user)
                if sub_att.submission.student_id not in allowed_students:
                    raise PermissionDenied("Cannot download another student's submission.")
            return sub_att
        raise DRFValidationError("Unsupported attachment kind.")
