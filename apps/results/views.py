"""Views and API ViewSets for Grading Scales, Tabulation, Exam Results, and Cumulative Standing."""

from decimal import Decimal
from typing import cast

from django.db.models import Count
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.permissions import DenyAll
from apps.exams.models import Exam
from apps.institutions.models import Institution
from apps.results.models import (
    CumulativeResult,
    ExamResult,
    GradingScale,
    ReportCard,
    ResultPublication,
    StudentOptionalSubject,
    SubjectResult,
    TabulationSheet,
    TermWeightageRule,
)
from apps.results.permissions import (
    CanCalculateResults,
    CanManageGrading,
    CanPublishResults,
    CanViewResults,
)
from apps.results.serializers import (
    CumulativeCalculateSerializer,
    CumulativeResultSerializer,
    ExamResultCalculateSerializer,
    ExamResultSerializer,
    GradingScaleSerializer,
    PromotionEligibilityResponseSerializer,
    PublicResultSearchSerializer,
    ReportCardBulkZipSerializer,
    ReportCardGenerateSerializer,
    ReportCardSerializer,
    ResultApproveSerializer,
    ResultPublicationSerializer,
    ResultPublishSerializer,
    StudentOptionalSubjectSerializer,
    SubjectResultSerializer,
    TabulationGenerateSerializer,
    TabulationSheetSerializer,
    TermWeightageRuleSerializer,
    WeakStudentsResponseSerializer,
)
from apps.results.services import (
    approve_exam_results,
    create_or_update_report_card,
    create_tabulation_sheet_record,
    generate_bulk_report_cards_zip,
    get_promotion_eligibility_feed,
    get_weak_students_analytics,
    publish_exam_results,
    seed_default_bd_grading_scale,
    tabulate_cumulative_results,
    tabulate_exam_results,
    unpublish_exam_results,
)
from apps.results.tasks import (
    calculate_cumulative_results_task,
    calculate_exam_results_task,
    generate_bulk_report_cards_task,
    generate_tabulation_sheet_task,
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
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "seed_bd_defaults",
        ]:
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
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "exam",
        "student",
        "exam_subject",
        "is_passed",
        "is_fourth_subject",
        "letter_grade",
    ]
    search_fields = [
        "student__name_en",
        "student__student_id",
        "exam_subject__subject__name_en",
    ]
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
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["exam", "student", "is_passed", "final_grade", "status"]
    search_fields = [
        "student__name_en",
        "student__student_id",
        "enrollment__section__name",
    ]
    ordering_fields = [
        "class_position",
        "section_position",
        "final_gpa",
        "total_marks",
    ]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return ExamResult.objects.none()

        qs = ExamResult.objects.filter(institution_id=inst_id, is_deleted=False).select_related(
            "student",
            "exam",
            "enrollment__section",
            "enrollment__class_level",
        )

        # Enforce student/guardian visibility filters
        if user and hasattr(user, "user_roles"):
            roles = set(user.user_roles.values_list("role__code", flat=True))
            if "student" in roles and not any(
                r in roles for r in ["admin", "teacher", "principal"]
            ):
                stu_profile = getattr(user, "student_profile", None)
                if not stu_profile:
                    return qs.none()
                qs = qs.filter(
                    student_id=stu_profile.id,
                    exam__publication__is_published=True,
                    exam__publication__is_visible_to_students=True,
                )
            elif "guardian" in roles and not any(
                r in roles for r in ["admin", "teacher", "principal"]
            ):
                guardians = (
                    list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
                )
                wards = []
                for g in guardians:
                    if hasattr(g, "students"):
                        wards.extend(list(g.students.values_list("id", flat=True)))
                qs = qs.filter(
                    student_id__in=wards,
                    exam__publication__is_published=True,
                    exam__publication__is_visible_to_guardians=True,
                )

        return qs.order_by("class_position", "section_position", "-final_gpa")

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
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "session",
        "class_level",
        "is_passed",
        "promotion_recommended",
    ]
    search_fields = ["student__name_en", "student__student_id"]
    ordering_fields = [
        "final_class_position",
        "final_section_position",
        "cumulative_gpa",
    ]

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
        request=CumulativeCalculateSerializer,
        summary="Trigger annual cumulative CGPA calculation",
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


class TabulationSheetViewSet(viewsets.ModelViewSet):
    """Archived and downloadable class tabulation broadsheets (Excel and PDF)."""

    serializer_class = TabulationSheetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["exam", "class_level", "section", "file_format"]
    ordering_fields = ["generated_at", "version"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return TabulationSheet.objects.none()
        return (
            TabulationSheet.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related("exam", "class_level", "section")
            .order_by("-generated_at")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve", "download"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action in ["generate", "create", "destroy"]:
            return [IsAuthenticated(), CanCalculateResults()]
        return [DenyAll()]

    @extend_schema(
        request=TabulationGenerateSerializer,
        summary="Generate broadsheet tabulation sheet (Excel or PDF)",
    )
    @action(detail=False, methods=["post"])
    def generate(self, request: Request) -> Response:
        serializer = TabulationGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam_id = str(serializer.validated_data["exam_id"])
        class_level_id = str(serializer.validated_data["class_level_id"])
        section_id = serializer.validated_data.get("section_id")
        file_format = serializer.validated_data.get("file_format", "xlsx")
        async_mode = serializer.validated_data.get("async_mode", False)

        if async_mode:
            task = generate_tabulation_sheet_task.delay(
                exam_id=exam_id,
                class_level_id=class_level_id,
                section_id=str(section_id) if section_id else None,
                file_format=file_format,
                user_id=str(request.user.id),
            )
            return Response(
                {
                    "status": "queued",
                    "task_id": task.id,
                    "message": "Tabulation sheet generation queued.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        record = create_tabulation_sheet_record(
            exam_id=exam_id,
            class_level_id=class_level_id,
            section_id=section_id,
            file_format=file_format,
            user=cast(User, request.user),
        )
        return Response(
            TabulationSheetSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Download tabulation sheet file directly")
    @action(detail=True, methods=["get"])
    def download(self, request: Request, pk=None) -> HttpResponse:
        sheet = self.get_object()
        if not sheet.file:
            raise ValidationError("Tabulation file not found.")
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if sheet.file_format == "xlsx"
            else "application/pdf"
        )
        response = HttpResponse(sheet.file.read(), content_type=content_type)
        filename = sheet.file.name.split("/")[-1]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ReportCardViewSet(viewsets.ModelViewSet):
    """Printable progress report card management, single PDF generation, and bulk ZIP download."""

    serializer_class = ReportCardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["exam", "student"]
    search_fields = ["student__name_en", "student__student_id"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return ReportCard.objects.none()

        qs = ReportCard.objects.filter(institution_id=inst_id, is_deleted=False).select_related(
            "exam",
            "student",
            "enrollment__class_level",
            "enrollment__section",
        )

        if user and hasattr(user, "user_roles"):
            roles = set(user.user_roles.values_list("role__code", flat=True))
            if "student" in roles and not any(
                r in roles for r in ["admin", "teacher", "principal"]
            ):
                stu_profile = getattr(user, "student_profile", None)
                if not stu_profile:
                    return qs.none()
                qs = qs.filter(
                    student_id=stu_profile.id,
                    exam__publication__is_published=True,
                    exam__publication__is_visible_to_students=True,
                )
            elif "guardian" in roles and not any(
                r in roles for r in ["admin", "teacher", "principal"]
            ):
                guardians = (
                    list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
                )
                wards = []
                for g in guardians:
                    if hasattr(g, "students"):
                        wards.extend(list(g.students.values_list("id", flat=True)))
                qs = qs.filter(
                    student_id__in=wards,
                    exam__publication__is_published=True,
                    exam__publication__is_visible_to_guardians=True,
                )

        return qs.order_by("-generated_at")

    def get_permissions(self):
        if self.action in ["list", "retrieve", "download"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action in ["generate", "bulk_zip", "create", "destroy"]:
            return [IsAuthenticated(), CanCalculateResults()]
        return [DenyAll()]

    @extend_schema(
        request=ReportCardGenerateSerializer,
        summary="Generate progress report card PDF for a student result",
    )
    @action(detail=False, methods=["post"])
    def generate(self, request: Request) -> Response:
        serializer = ReportCardGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam_result_id = serializer.validated_data["exam_result_id"]
        template_style = serializer.validated_data.get("template_style", "default_bd")

        card = create_or_update_report_card(
            exam_result_id=exam_result_id,
            template_style=template_style,
            user=cast(User, request.user),
        )
        return Response(ReportCardSerializer(card).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Download progress report card PDF directly")
    @action(detail=True, methods=["get"])
    def download(self, request: Request, pk=None) -> HttpResponse:
        card = self.get_object()
        if not card.file:
            raise ValidationError("Report card file not found.")
        response = HttpResponse(card.file.read(), content_type="application/pdf")
        filename = card.file.name.split("/")[-1]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @extend_schema(
        request=ReportCardBulkZipSerializer,
        summary="Batch-generate and download report cards in a ZIP archive",
    )
    @action(detail=False, methods=["post"])
    def bulk_zip(self, request: Request) -> HttpResponse | Response:
        serializer = ReportCardBulkZipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam_id = str(serializer.validated_data["exam_id"])
        class_level_id = str(serializer.validated_data["class_level_id"])
        section_id = serializer.validated_data.get("section_id")
        async_mode = serializer.validated_data.get("async_mode", False)

        if async_mode:
            task = generate_bulk_report_cards_task.delay(
                exam_id=exam_id,
                class_level_id=class_level_id,
                section_id=str(section_id) if section_id else None,
                user_id=str(request.user.id),
            )
            return Response(
                {
                    "status": "queued",
                    "task_id": task.id,
                    "message": "Bulk report card generation queued.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        zip_bytes = generate_bulk_report_cards_zip(
            exam_id=exam_id,
            class_level_id=class_level_id,
            section_id=section_id,
            user=cast(User, request.user),
        )
        response = HttpResponse(zip_bytes, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="report_cards_{exam_id}.zip"'
        return response


class ResultPublicationViewSet(viewsets.ModelViewSet):
    """Examination publication workflow: approval, formal release, and visibility schedule."""

    serializer_class = ResultPublicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["exam", "is_published"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        inst_id = getattr(user, "institution_id", None)
        if not inst_id:
            return ResultPublication.objects.none()
        return (
            ResultPublication.objects.filter(institution_id=inst_id, is_deleted=False)
            .select_related("exam")
            .order_by("-published_at")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), CanViewResults()]
        if self.action in ["approve", "publish", "unpublish"]:
            return [IsAuthenticated(), CanPublishResults()]
        return [DenyAll()]

    @extend_schema(
        request=ResultApproveSerializer,
        summary="Approve exam results (Principal / Head Teacher)",
    )
    @action(detail=False, methods=["post"])
    def approve(self, request: Request) -> Response:
        serializer = ResultApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam_id = serializer.validated_data["exam_id"]
        res = approve_exam_results(exam_id=exam_id, user=cast(User, request.user))
        return Response(res, status=status.HTTP_200_OK)

    @extend_schema(
        request=ResultPublishSerializer,
        summary="Formally publish examination results to student/guardian portals",
    )
    @action(detail=False, methods=["post"])
    def publish(self, request: Request) -> Response:
        serializer = ResultPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = publish_exam_results(
            exam_id=serializer.validated_data["exam_id"],
            user=cast(User, request.user),
            is_visible_to_guardians=serializer.validated_data.get("is_visible_to_guardians", True),
            is_visible_to_students=serializer.validated_data.get("is_visible_to_students", True),
            allow_public_search=serializer.validated_data.get("allow_public_search", False),
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(res, status=status.HTTP_200_OK)

    @extend_schema(
        request=ResultApproveSerializer,
        summary="Revert published results back to draft for mark corrections",
    )
    @action(detail=False, methods=["post"])
    def unpublish(self, request: Request) -> Response:
        serializer = ResultApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = unpublish_exam_results(
            exam_id=serializer.validated_data["exam_id"],
            user=cast(User, request.user),
        )
        return Response(res, status=status.HTTP_200_OK)


class PublicResultSearchView(APIView):
    """Public, rate-limited result lookup endpoint for students/guardians by roll or Student ID."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[PublicResultSearchSerializer],
        responses={200: ExamResultSerializer},
        summary="Public student result lookup by roll or student ID",
    )
    def get(self, request: Request) -> Response:
        serializer = PublicResultSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        exam_id = serializer.validated_data["exam_id"]
        student_id = serializer.validated_data.get("student_id")
        roll_no = serializer.validated_data.get("roll_no")

        if not student_id and roll_no is None:
            raise ValidationError({"student_id": "Either student_id or roll_no must be provided."})

        # Check if exam is published with public search permitted
        pub = ResultPublication.objects.filter(
            exam_id=exam_id, is_published=True, allow_public_search=True
        ).first()
        if not pub:
            raise PermissionDenied("Public result lookup is not enabled for this examination.")

        res_qs = ExamResult.objects.filter(exam_id=exam_id, is_deleted=False)
        if student_id:
            res_qs = res_qs.filter(student__student_id=student_id)
        if roll_no is not None:
            res_qs = res_qs.filter(enrollment__roll_no=roll_no)

        result = res_qs.first()
        if not result:
            return Response(
                {"message": "No result found for the specified student."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ExamResultSerializer(result).data)


class ResultAnalyticsViewSet(viewsets.ViewSet):
    """Diagnostic academic analytics: weak-student identification and promotion feeds."""

    permission_classes = [IsAuthenticated, CanViewResults]

    @extend_schema(
        summary="Retrieve weak students at academic risk for an exam",
        responses={200: WeakStudentsResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def weak_students(self, request: Request) -> Response:
        exam_id = request.query_params.get("exam_id")
        if not exam_id:
            raise ValidationError({"exam_id": "exam_id query param is required."})

        gpa_thresh_param = request.query_params.get("gpa_threshold", "2.00")
        try:
            gpa_thresh = Decimal(gpa_thresh_param)
        except Exception:
            gpa_thresh = Decimal("2.00")

        res = get_weak_students_analytics(exam_id=exam_id, gpa_threshold=gpa_thresh)
        return Response(res, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Retrieve promotion recommendations feed based on annual CGPA & attendance",
        responses={200: PromotionEligibilityResponseSerializer},
    )
    @action(detail=False, methods=["get"])
    def promotion_eligibility(self, request: Request) -> Response:
        session_id = request.query_params.get("session_id")
        class_level_id = request.query_params.get("class_level_id")
        if not session_id or not class_level_id:
            raise ValidationError(
                {"error": "session_id and class_level_id query params are required."}
            )

        min_cgpa_param = request.query_params.get("min_cgpa", "2.00")
        min_att_param = request.query_params.get("min_attendance_pct", "70.00")
        try:
            min_cgpa = Decimal(min_cgpa_param)
            min_att = Decimal(min_att_param)
        except Exception:
            min_cgpa = Decimal("2.00")
            min_att = Decimal("70.00")

        res = get_promotion_eligibility_feed(
            session_id=session_id,
            class_level_id=class_level_id,
            min_cgpa=min_cgpa,
            min_attendance_pct=min_att,
        )
        return Response(res, status=status.HTTP_200_OK)
