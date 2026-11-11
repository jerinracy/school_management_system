"""API ViewSets for exam configurations, routines, seat plans, admit cards, and mark entries."""

from typing import cast

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.mixins import TenantScopedMixin
from apps.exams.models import (
    AdmitCard,
    Exam,
    ExamEligibilityPolicy,
    ExamRoutine,
    ExamSubject,
    ExamType,
    GraceMarkRule,
    MarkEntry,
    ReScrutinyRequest,
    ReScrutinyStatus,
    SeatPlan,
    StudentExamEligibility,
)
from apps.exams.permissions import (
    CanEnterMarks,
    CanLockMarks,
    CanManageExams,
    CanViewExams,
)
from apps.exams.serializers import (
    AdmitCardSerializer,
    BulkMarkSubmitSerializer,
    ExamEligibilityPolicySerializer,
    ExamRoutineSerializer,
    ExamSerializer,
    ExamSubjectSerializer,
    ExamTypeSerializer,
    GraceMarkRuleSerializer,
    MarkEntrySerializer,
    MarkLockSerializer,
    MarkUnlockSerializer,
    ReScrutinyRequestSerializer,
    ReScrutinyReviewSerializer,
    SeatPlanGenerateSerializer,
    SeatPlanSerializer,
    StudentExamEligibilitySerializer,
)
from apps.exams.services import (
    bulk_save_marks,
    evaluate_exam_eligibility_for_exam,
    export_mark_entry_excel,
    generate_admit_card_pdf,
    generate_admit_cards_for_eligible_students,
    generate_seat_plans_for_exam,
    import_mark_entry_excel,
    lock_exam_subject_marks,
    save_single_mark_entry,
    unlock_exam_subject_marks,
)


class ExamTypeViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for institutional exam types (Half-Yearly, Final, Model Test)."""

    queryset = ExamType.objects.all()
    serializer_class = ExamTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_board_exam"]
    search_fields = ["name", "code"]
    ordering = ["name"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]


class ExamViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Examination lifecycle management: scheduling, eligibility, seat planning, progress."""

    queryset = (
        Exam.objects.select_related("exam_type", "session").prefetch_related("target_classes").all()
    )
    serializer_class = ExamSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["session", "exam_type", "status", "is_active"]
    search_fields = ["name", "term"]
    ordering = ["-start_date", "name"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]

    @action(detail=True, methods=["post"], url_path="generate_eligibility")
    def generate_eligibility(self, request: Request, pk: str | None = None) -> Response:
        """Calculate student attendance percentages and evaluate exam eligibility."""
        exam = self.get_object()
        records = evaluate_exam_eligibility_for_exam(exam.id)
        serializer = StudentExamEligibilitySerializer(records, many=True)
        return Response(
            {
                "message": f"Successfully evaluated eligibility for {len(records)} students.",
                "total_evaluated": len(records),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="generate_admit_cards")
    def generate_admit_cards(self, request: Request, pk: str | None = None) -> Response:
        """Issue Admit Cards for all eligible students."""
        exam = self.get_object()
        cards = generate_admit_cards_for_eligible_students(exam.id)
        serializer = AdmitCardSerializer(cards, many=True)
        return Response(
            {
                "message": f"Successfully generated {len(cards)} admit cards.",
                "total_issued": len(cards),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="generate_seat_plans")
    def generate_seat_plans(self, request: Request, pk: str | None = None) -> Response:
        """Generate room and bench seat allocations for students."""
        exam = self.get_object()
        serializer = SeatPlanGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plans = generate_seat_plans_for_exam(
            exam_id=exam.id,
            room_configs=serializer.validated_data["room_configs"],
            interleave=serializer.validated_data.get("interleave", True),
            exam_subject_id=serializer.validated_data.get("exam_subject_id"),
        )
        plan_serializer = SeatPlanSerializer(plans, many=True)
        return Response(
            {
                "message": f"Successfully seated {len(plans)} students.",
                "total_allocated": len(plans),
                "data": plan_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="progress")
    def progress(self, request: Request, pk: str | None = None) -> Response:
        """Track mark entry progress across subjects in this exam."""
        exam = self.get_object()
        subjects = ExamSubject.objects.filter(exam=exam).select_related("class_level", "subject")

        progress_data = []
        for s in subjects:
            total_marks_count = MarkEntry.objects.filter(exam_subject=s).count()
            entered_count = MarkEntry.objects.filter(
                exam_subject=s,
                total_marks__isnull=False,
            ).count()

            progress_data.append(
                {
                    "exam_subject_id": str(s.id),
                    "class_name": s.class_level.name,
                    "subject_name": s.subject.name_en,
                    "is_locked": s.is_marks_locked,
                    "total_entries": total_marks_count,
                    "completed_entries": entered_count,
                    "completion_rate": (
                        round((entered_count / total_marks_count * 100), 1)
                        if total_marks_count > 0
                        else 0.0
                    ),
                }
            )

        return Response({"exam_id": str(exam.id), "subjects_progress": progress_data})


class ExamSubjectViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for exam-specific subject configurations, pass marks, and assigned evaluators."""

    queryset = ExamSubject.objects.select_related(
        "exam", "class_level", "subject", "assigned_teacher"
    ).all()
    serializer_class = ExamSubjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam", "class_level", "subject", "assigned_teacher", "is_marks_locked"]
    search_fields = ["subject__name_en", "class_level__name"]
    ordering = ["exam_date", "start_time", "subject__name_en"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]


class ExamRoutineViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Exam schedule and timetable."""

    queryset = ExamRoutine.objects.select_related(
        "exam", "exam_subject__subject", "exam_subject__class_level"
    ).all()
    serializer_class = ExamRoutineSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam", "exam_subject", "exam_date"]
    ordering = ["exam_date", "start_time"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]


class ExamEligibilityPolicyViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Attendance and fees eligibility threshold policies."""

    queryset = ExamEligibilityPolicy.objects.select_related("exam").all()
    serializer_class = ExamEligibilityPolicySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["exam"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams]


class StudentExamEligibilityViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only and clearance update endpoints for student exam qualifications."""

    queryset = StudentExamEligibility.objects.select_related("exam", "student").all()
    serializer_class = StudentExamEligibilitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam", "clearance_status", "dues_cleared"]
    search_fields = ["student__name_en", "student__student_id"]
    ordering = ["student__student_id"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]


class SeatPlanViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Seating arrangement inspection."""

    queryset = SeatPlan.objects.select_related("exam", "student", "class_level", "section").all()
    serializer_class = SeatPlanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam", "exam_subject", "room_number", "class_level", "section"]
    search_fields = ["student__name_en", "student__student_id", "room_number"]
    ordering = ["room_number", "bench_label", "seat_number"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]


class AdmitCardViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Admit card inspection and PDF generation."""

    queryset = AdmitCard.objects.select_related("exam", "student").all()
    serializer_class = AdmitCardSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam", "is_issued"]
    search_fields = ["student__name_en", "student__student_id", "card_number"]
    ordering = ["card_number"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]

    @action(detail=True, methods=["get"], url_path="download_pdf")
    def download_pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        """Download high-resolution Bangla Admit Card PDF."""
        card = self.get_object()
        pdf_bytes = generate_admit_card_pdf(card.id)
        filename = f"admit_card_{card.card_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class MarkEntryViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Examination mark entry, bulk grid intake, locking, and Excel sync."""

    queryset = MarkEntry.objects.select_related(
        "exam_subject__subject", "student", "entered_by"
    ).all()
    serializer_class = MarkEntrySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam_subject", "is_absent", "is_locked"]
    search_fields = ["student__name_en", "student__student_id"]
    ordering = ["student__student_id"]
    permission_classes = [permissions.IsAuthenticated, CanEnterMarks | CanManageExams]

    @action(detail=False, methods=["post"], url_path="bulk_save")
    def bulk_save(self, request: Request) -> Response:
        """Batch intake of student marks from UI table."""
        serializer = BulkMarkSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = cast(User, request.user)
        try:
            saved_count, errors = bulk_save_marks(
                exam_subject_id=serializer.validated_data["exam_subject_id"],
                entries_data=serializer.validated_data["entries"],
                user=user,
            )
        except (PermissionDenied, DjangoPermissionDenied):
            raise
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": f"Successfully recorded marks for {saved_count} students.",
                "saved_count": saved_count,
                "errors": errors,
            },
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="lock",
        permission_classes=[permissions.IsAuthenticated, CanLockMarks | CanManageExams],
    )
    def lock_marks(self, request: Request) -> Response:
        """Lock an ExamSubject to freeze teacher submissions."""
        serializer = MarkLockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = cast(User, request.user)
        exam_subj = lock_exam_subject_marks(
            exam_subject_id=serializer.validated_data["exam_subject_id"],
            user=user,
        )
        return Response({"message": f"Marks successfully locked for {exam_subj.subject.name_en}."})

    @action(
        detail=False,
        methods=["post"],
        url_path="unlock",
        permission_classes=[permissions.IsAuthenticated, CanLockMarks | CanManageExams],
    )
    def unlock_marks(self, request: Request) -> Response:
        """Administratively unlock an ExamSubject with audit justification."""
        serializer = MarkUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = cast(User, request.user)
        exam_subj = unlock_exam_subject_marks(
            exam_subject_id=serializer.validated_data["exam_subject_id"],
            user=user,
            reason=serializer.validated_data["reason"],
        )
        return Response({"message": f"Marks unlocked for {exam_subj.subject.name_en}."})

    @action(detail=False, methods=["get"], url_path="export_template")
    def export_template(self, request: Request) -> HttpResponse:
        """Download pre-filled Excel roll sheet for offline mark entry."""
        exam_subject_id = request.query_params.get("exam_subject_id")
        if not exam_subject_id:
            return HttpResponse("Missing exam_subject_id query parameter.", status=400)

        excel_bytes = export_mark_entry_excel(exam_subject_id)
        filename = f"marks_template_{exam_subject_id[:8]}.xlsx"
        response = HttpResponse(
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import_excel",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_excel(self, request: Request) -> Response:
        """Upload and process filled marks Excel spreadsheet."""
        exam_subject_id = request.data.get("exam_subject_id")
        uploaded_file = request.FILES.get("file")

        if not exam_subject_id or not uploaded_file:
            return Response(
                {"error": "Both 'exam_subject_id' and 'file' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = cast(User, request.user)
        imported_count, errors = import_mark_entry_excel(
            exam_subject_id=exam_subject_id,
            file_bytes=uploaded_file.read(),
            user=user,
        )

        return Response(
            {
                "message": f"Import complete: {imported_count} student marks recorded.",
                "imported_count": imported_count,
                "errors": errors,
            },
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )


class ReScrutinyRequestViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Student and guardian mark re-evaluation requests."""

    queryset = ReScrutinyRequest.objects.select_related(
        "student", "exam_subject__subject", "requested_by"
    ).all()
    serializer_class = ReScrutinyRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["exam_subject", "status", "fee_paid"]
    search_fields = ["student__name_en", "student__student_id"]
    ordering = ["-created_at"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams | CanViewExams]

    @action(
        detail=True,
        methods=["post"],
        url_path="review",
        permission_classes=[permissions.IsAuthenticated, CanManageExams],
    )
    def review(self, request: Request, pk: str | None = None) -> Response:
        """Administrative decision on mark re-scrutiny."""
        rescrutiny = self.get_object()
        serializer = ReScrutinyReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        rescrutiny.status = data["status"]
        rescrutiny.reviewer_notes = data.get("reviewer_notes", "")
        rescrutiny.resolved_at = timezone.now()

        if data["status"] == ReScrutinyStatus.APPROVED:
            # Update marks
            rescrutiny.revised_creative_marks = data.get("revised_creative_marks")
            rescrutiny.revised_mcq_marks = data.get("revised_mcq_marks")
            rescrutiny.revised_practical_marks = data.get("revised_practical_marks")

            user = cast(User, request.user)
            save_single_mark_entry(
                exam_subject=rescrutiny.exam_subject,
                student=rescrutiny.student,
                user=user,
                creative_marks=data.get("revised_creative_marks"),
                mcq_marks=data.get("revised_mcq_marks"),
                practical_marks=data.get("revised_practical_marks"),
                reason=f"Approved re-scrutiny application #{rescrutiny.id}",
            )

        rescrutiny.save()
        return Response(ReScrutinyRequestSerializer(rescrutiny).data)


class GraceMarkRuleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Institutional rules for awarding grace marks."""

    queryset = GraceMarkRule.objects.select_related("exam", "subject").all()
    serializer_class = GraceMarkRuleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["exam", "subject", "is_active"]
    permission_classes = [permissions.IsAuthenticated, CanManageExams]
