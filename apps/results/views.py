"""Views and API ViewSets for Grading Scales, Tabulation, Exam Results, and Cumulative Standing."""

from decimal import Decimal

from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.permissions import DenyAll
from apps.exams.models import Exam
from apps.institutions.models import Institution
from apps.results.models import (
    CumulativeResult,
    ExamResult,
    GradingScale,
    StudentOptionalSubject,
    SubjectResult,
    TermWeightageRule,
)
from apps.results.permissions import (
    CanCalculateResults,
    CanManageGrading,
    CanViewResults,
)
from apps.results.serializers import (
    CumulativeCalculateSerializer,
    CumulativeResultSerializer,
    ExamResultCalculateSerializer,
    ExamResultSerializer,
    GradingScaleSerializer,
    StudentOptionalSubjectSerializer,
    SubjectResultSerializer,
    TermWeightageRuleSerializer,
)
from apps.results.services import (
    seed_default_bd_grading_scale,
    tabulate_cumulative_results,
    tabulate_exam_results,
)
from apps.results.tasks import (
    calculate_cumulative_results_task,
    calculate_exam_results_task,
)


def _get_request_institution(request: Request) -> Institution:
    """Safely resolve current institution from request context."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    inst = getattr(user, "institution", None)
    if not inst:
        raise PermissionDenied("User does not belong to any institution.")
    return inst


class GradingScaleViewSet(viewsets.ModelViewSet):
    """Manage institutional grading scales and grade tier thresholds."""

    serializer_class = GradingScaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return GradingScale.objects.none()
        return (
            GradingScale.objects.filter(institution_id=inst_id, is_deleted=False)
            .prefetch_related("tiers")
            .order_by("-is_default", "name")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action in ["create", "update", "partial_update", "destroy", "seed_bd_defaults"]:
            return [IsAuthenticated(), CanManageGrading()]
        return [DenyAll()]

    def perform_create(self, serializer):
        inst = _get_request_institution(self.request)
        serializer.save(institution=inst)

    @extend_schema(summary="Seed standard Bangladesh National Curriculum (GPA 5.0) grading scale")
    @action(detail=False, methods=["post"])
    def seed_bd_defaults(self, request: Request) -> Response:
        inst = _get_request_institution(request)
        scale = seed_default_bd_grading_scale(institution=inst)
        return Response(GradingScaleSerializer(scale).data, status=status.HTTP_201_CREATED)


class StudentOptionalSubjectViewSet(viewsets.ModelViewSet):
    """Assign and manage optional 4th subjects for students in Class 9-12."""

    serializer_class = StudentOptionalSubjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["student", "session", "class_level", "subject"]
    search_fields = ["student__name_en", "student__student_id", "subject__name_en"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return StudentOptionalSubject.objects.none()
        return (
            StudentOptionalSubject.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related("student", "session", "class_level", "subject")
            .order_by("student__student_id")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanManageGrading()]
        return [DenyAll()]

    def perform_create(self, serializer):
        inst = _get_request_institution(self.request)
        serializer.save(institution=inst)


class SubjectResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for evaluated subject scores and grade points."""

    serializer_class = SubjectResultSerializer
    permission_classes = [IsAuthenticated, CanViewResults]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "exam",
        "student",
        "exam_subject",
        "is_passed",
        "is_fourth_subject",
        "letter_grade",
    ]
    search_fields = ["student__name_en", "student__student_id", "exam_subject__subject__name_en"]
    ordering_fields = ["grade_point", "total_marks", "marks_percentage"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return SubjectResult.objects.none()
        return (
            SubjectResult.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related(
                "student",
                "exam",
                "exam_subject__subject",
            )
            .order_by("exam_subject__subject__name_en")
        )


class ExamResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Student exam results summary, ranking, and tabulation execution endpoint."""

    serializer_class = ExamResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam", "student", "is_passed", "final_grade", "status"]
    search_fields = ["student__name_en", "student__student_id", "enrollment__section__name"]
    ordering_fields = ["class_position", "section_position", "final_gpa", "total_marks"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return ExamResult.objects.none()
        return (
            ExamResult.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related(
                "student",
                "exam",
                "enrollment__section",
                "enrollment__class_level",
            )
            .order_by("class_position", "section_position", "-final_gpa")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve", "summary"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action == "calculate":
            return [IsAuthenticated(), CanCalculateResults()]
        return [DenyAll()]

    @extend_schema(
        request=ExamResultCalculateSerializer,
        summary="Trigger result tabulation and ranking for an exam",
    )
    @action(detail=False, methods=["post"])
    def calculate(self, request: Request) -> Response:
        inst = _get_request_institution(request)
        serializer = ExamResultCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam_id = str(serializer.validated_data["exam_id"])
        async_mode = serializer.validated_data.get("async_mode", False)

        exam = Exam.objects.filter(id=exam_id, institution=inst).first()
        if not exam:
            raise ValidationError({"exam_id": "Examination not found."})

        if async_mode:
            task = calculate_exam_results_task.delay(exam_id)
            return Response(
                {
                    "status": "queued",
                    "task_id": task.id,
                    "message": "Result calculation queued in background.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        res = tabulate_exam_results(exam_id=exam_id)
        if res.get("status") == "error":
            return Response(res, status=status.HTTP_400_BAD_REQUEST)
        return Response(res, status=status.HTTP_200_OK)

    @extend_schema(summary="Get statistical overview of exam performance and GPA distribution")
    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        exam_id = request.query_params.get("exam_id")
        if not exam_id:
            raise ValidationError({"exam_id": "exam_id query parameter is required."})

        qs = self.get_queryset().filter(exam_id=exam_id)
        total = qs.count()
        if total == 0:
            return Response(
                {
                    "total_students": 0,
                    "passed_count": 0,
                    "failed_count": 0,
                    "pass_percentage": Decimal("0.00"),
                    "gpa_5_count": 0,
                    "gpa_distribution": {},
                }
            )

        passed = qs.filter(is_passed=True).count()
        failed = total - passed
        pass_pct = Decimal(str((passed / total) * 100)).quantize(Decimal("0.01"))
        gpa_5 = qs.filter(final_gpa=Decimal("5.00")).count()

        # Grade distribution
        dist = qs.values("final_grade").annotate(count=Count("id")).order_by("final_grade")
        dist_dict = {item["final_grade"]: item["count"] for item in dist}

        return Response(
            {
                "total_students": total,
                "passed_count": passed,
                "failed_count": failed,
                "pass_percentage": pass_pct,
                "gpa_5_count": gpa_5,
                "gpa_distribution": dist_dict,
            }
        )


class TermWeightageRuleViewSet(viewsets.ModelViewSet):
    """Configure multi-term weightage percentages for annual CGPA calculation."""

    serializer_class = TermWeightageRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["session", "class_level", "exam"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return TermWeightageRule.objects.none()
        return (
            TermWeightageRule.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related("session", "class_level", "exam")
            .order_by("class_level", "exam__start_date")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanManageGrading()]
        return [DenyAll()]

    def perform_create(self, serializer):
        inst = _get_request_institution(self.request)
        serializer.save(institution=inst)


class CumulativeResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Annual session cumulative CGPA standings and promotion recommendations."""

    serializer_class = CumulativeResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["session", "class_level", "is_passed", "promotion_recommended"]
    search_fields = ["student__name_en", "student__student_id"]
    ordering_fields = ["final_class_position", "final_section_position", "cumulative_gpa"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return CumulativeResult.objects.none()
        return (
            CumulativeResult.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related(
                "student",
                "session",
                "class_level",
                "enrollment__section",
            )
            .order_by("final_class_position", "final_section_position")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action == "calculate":
            return [IsAuthenticated(), CanCalculateResults()]
        return [DenyAll()]

    @extend_schema(
        request=CumulativeCalculateSerializer, summary="Trigger annual cumulative CGPA calculation"
    )
    @action(detail=False, methods=["post"])
    def calculate(self, request: Request) -> Response:
        serializer = CumulativeCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = str(serializer.validated_data["session_id"])
        class_level_id = str(serializer.validated_data["class_level_id"])
        async_mode = serializer.validated_data.get("async_mode", False)

        if async_mode:
            task = calculate_cumulative_results_task.delay(session_id, class_level_id)
            return Response(
                {
                    "status": "queued",
                    "task_id": task.id,
                    "message": "Cumulative calculation queued.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        res = tabulate_cumulative_results(session_id=session_id, class_level_id=class_level_id)
        if res.get("status") == "error":
            return Response(res, status=status.HTTP_400_BAD_REQUEST)
        return Response(res, status=status.HTTP_200_OK)
