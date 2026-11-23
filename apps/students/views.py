"""API views for Student Management."""

import io
from typing import Any

import openpyxl
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import TenantScopedMixin
from apps.core.pagination import StandardResultsSetPagination
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import (
    PromotionBatch,
    Student,
    StudentEnrollment,
    Testimonial,
    TransferCertificate,
)
from apps.students.permissions import (
    CanManageStudents,
    CanViewStudentsOrTeacher,
    IsGuardianOfStudent,
)
from apps.students.serializers import (
    AdmitFromApplicationSerializer,
    AutoAssignRollsSerializer,
    BulkImportSerializer,
    IssueTCSerializer,
    IssueTestimonialSerializer,
    PromotionBatchSerializer,
    PromotionPreviewRequestSerializer,
    StudentAssignLoginSerializer,
    StudentCreateUpdateSerializer,
    StudentDetailSerializer,
    StudentEnrollmentBriefSerializer,
    StudentEnrollmentCreateUpdateSerializer,
    StudentIDCardSerializer,
    StudentListSerializer,
    TestimonialSerializer,
    TransferCertificateSerializer,
)
from apps.students.services import (
    admit_from_application,
    apply_promotion,
    auto_assign_section_rolls,
    create_portal_user_for_student,
    import_students_from_excel,
    issue_or_renew_id_card,
    issue_testimonial,
    issue_transfer_certificate,
    preview_promotion,
    rollback_promotion,
)


def _get_request_institution(request: Request) -> Institution:
    user = request.user
    if not hasattr(user, "institution") or user.institution is None:
        raise ValidationError("User has no associated institution.")
    return user.institution


@extend_schema_view(
    list=extend_schema(summary="List students", tags=["Students"]),
    retrieve=extend_schema(summary="Retrieve student details", tags=["Students"]),
    create=extend_schema(summary="Create a new student", tags=["Students"]),
    update=extend_schema(summary="Update student profile", tags=["Students"]),
    partial_update=extend_schema(summary="Partially update student profile", tags=["Students"]),
    destroy=extend_schema(summary="Soft-delete student", tags=["Students"]),
)
class StudentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Endpoints for student lifecycle management."""

    queryset = (
        Student.objects.all()
        .select_related("institution")
        .prefetch_related("enrollments", "guardian_relations__guardian")
    )
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "gender", "religion", "blood_group"]
    search_fields = ["student_id", "name_en", "name_bn", "birth_reg_no", "emergency_contact_phone"]
    ordering_fields = ["student_id", "name_en", "admission_date", "created_at"]
    ordering = ["student_id"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve", "me"]:
            return [IsAuthenticated(), (CanViewStudentsOrTeacher | IsGuardianOfStudent)()]
        return [IsAuthenticated(), CanManageStudents()]

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        section_id = self.request.query_params.get("section") or self.request.query_params.get(
            "section_id"
        )
        session_id = self.request.query_params.get("session") or self.request.headers.get(
            "X-Academic-Session"
        )
        class_id = self.request.query_params.get("class_level") or self.request.query_params.get(
            "class_id"
        )

        if not session_id:
            inst = _get_request_institution(self.request)
            active_session = AcademicSession.objects.filter(
                institution=inst, is_current=True, is_deleted=False
            ).first()
            if active_session:
                session_id = str(active_session.id)

        if section_id:
            qs = qs.filter(
                enrollments__section_id=section_id,
                enrollments__status="active",
                enrollments__is_deleted=False,
            )
        if session_id and session_id != "all":
            qs = qs.filter(
                enrollments__session_id=session_id,
                enrollments__status="active",
                enrollments__is_deleted=False,
            )
        if class_id:
            qs = qs.filter(
                enrollments__class_level_id=class_id,
                enrollments__status="active",
                enrollments__is_deleted=False,
            )
        return qs.distinct()

    @extend_schema(
        summary="Retrieve logged-in student profile",
        tags=["Students"],
        responses={200: StudentDetailSerializer},
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        user = request.user
        student = None
        if hasattr(user, "student_profile") and user.student_profile:
            student = user.student_profile
        elif hasattr(user, "phone") and user.phone:
            inst = _get_request_institution(request)
            student = Student.objects.filter(institution=inst, phone=user.phone).first()

        if student:
            serializer = StudentDetailSerializer(student, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "No student profile linked to this user."}, status=status.HTTP_404_NOT_FOUND
        )

    def get_serializer_class(self) -> type[Any]:
        if self.action == "list":
            return StudentListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return StudentCreateUpdateSerializer
        return StudentDetailSerializer

    def perform_destroy(self, instance: Student) -> None:
        if instance.user:
            instance.user.is_active = False
            instance.user.save(update_fields=["is_active"])
        instance.delete()

    @extend_schema(summary="Admit applicant from admission module", tags=["Students"])
    @action(detail=False, methods=["post"], url_path="admit-from-application")
    def admit_application(self, request: Request) -> Response:
        serializer = AdmitFromApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        student, enrollment = admit_from_application(
            application_id=data["application_id"],
            section_id=data["section_id"],
            roll_no=data["roll_no"],
            session_id=data.get("session_id"),
            student_id=data.get("student_id"),
        )

        return Response(
            {
                "message": f"Student {student.student_id} successfully enrolled.",
                "student": StudentListSerializer(student).data,
                "enrollment": StudentEnrollmentBriefSerializer(enrollment).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Bulk import students from Excel",
        tags=["Students"],
        request=BulkImportSerializer,
    )
    @action(
        detail=False, methods=["post"], parser_classes=[MultiPartParser], url_path="bulk-import"
    )
    def bulk_import(self, request: Request) -> Response:
        serializer = BulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        dry_run = serializer.validated_data.get("dry_run", True)
        institution = _get_request_institution(request)

        file_bytes = uploaded_file.read()
        result = import_students_from_excel(
            institution_id=institution.id,
            file_bytes=file_bytes,
            dry_run=dry_run,
        )

        resp_status = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=resp_status)

    @extend_schema(summary="Export students to Excel", tags=["Students"])
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request: Request) -> HttpResponse:
        queryset = self.filter_queryset(self.get_queryset())
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Students"

        headers = [
            "Student ID",
            "Name (EN)",
            "Name (BN)",
            "DOB",
            "Gender",
            "Blood Group",
            "Birth Reg No",
            "Status",
            "Admission Date",
            "Emergency Phone",
        ]
        ws.append(headers)

        for s in queryset:
            ws.append(
                [
                    s.student_id,
                    s.name_en,
                    s.name_bn,
                    str(s.dob),
                    s.gender,
                    s.blood_group,
                    s.birth_reg_no or "",
                    s.status,
                    str(s.admission_date),
                    s.emergency_contact_phone,
                ]
            )

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="students_export.xlsx"'
        return response

    @extend_schema(summary="Generate or download Student ID Card", tags=["Students"])
    @action(detail=True, methods=["get", "post"], url_path="id-card")
    def id_card(self, request: Request, pk: str | None = None) -> HttpResponse | Response:
        student = self.get_object()
        card, pdf_bytes = issue_or_renew_id_card(student_id=student.id)

        if request.query_params.get("download") == "pdf" or request.method == "GET":
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="ID_CARD_{card.card_no}.pdf"'
            return response

        return Response(
            {
                "message": "ID card generated successfully.",
                "card": StudentIDCardSerializer(card).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Assign or Reset Student App Login",
        tags=["Students"],
        request=StudentAssignLoginSerializer,
        responses={200: dict},
    )
    @action(detail=True, methods=["post"], url_path="assign-login")
    def assign_login(self, request: Request, pk: str | None = None) -> Response:
        student = self.get_object()
        serializer = StudentAssignLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data.get("phone")
        password = serializer.validated_data["password"]

        user, final_password = create_portal_user_for_student(
            student, phone=phone, password=password
        )
        return Response(
            {
                "message": "Student app login details set successfully.",
                "user_id": str(user.id),
                "phone": user.phone,
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(summary="List student enrollments", tags=["Students - Enrollments"]),
    retrieve=extend_schema(summary="Retrieve enrollment details", tags=["Students - Enrollments"]),
    create=extend_schema(summary="Create a student enrollment", tags=["Students - Enrollments"]),
    update=extend_schema(summary="Update student enrollment", tags=["Students - Enrollments"]),
    partial_update=extend_schema(
        summary="Partially update student enrollment", tags=["Students - Enrollments"]
    ),
    destroy=extend_schema(summary="Delete student enrollment", tags=["Students - Enrollments"]),
)
class StudentEnrollmentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Student enrollment records."""

    queryset = (
        StudentEnrollment.objects.all()
        .select_related("student", "session", "class_level", "section", "shift", "group")
        .order_by("session", "class_level", "section", "roll_no")
    )
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student", "session", "class_level", "section", "status"]
    ordering_fields = ["roll_no", "enrollment_date"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), CanViewStudentsOrTeacher()]
        return [IsAuthenticated(), CanManageStudents()]

    def get_serializer_class(self) -> type[Any]:
        if self.action in ["create", "update", "partial_update"]:
            return StudentEnrollmentCreateUpdateSerializer
        return StudentEnrollmentBriefSerializer

    @extend_schema(summary="Auto re-sequence rolls in a section", tags=["Students - Enrollments"])
    @action(detail=False, methods=["post"], url_path="auto-assign-rolls")
    def auto_assign_rolls(self, request: Request) -> Response:
        serializer = AutoAssignRollsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        enrollments = auto_assign_section_rolls(
            section_id=data["section_id"],
            session_id=data["session_id"],
            strategy=data.get("strategy", "name_en"),
        )

        return Response(
            {
                "message": f"Successfully re-sequenced {len(enrollments)} rolls.",
                "enrollments": StudentEnrollmentBriefSerializer(enrollments, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(summary="List promotion batches", tags=["Students - Promotions"]),
    retrieve=extend_schema(summary="Retrieve promotion batch", tags=["Students - Promotions"]),
)
class PromotionViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Academic promotion batches."""

    queryset = PromotionBatch.objects.all().select_related(
        "from_session", "to_session", "from_class", "to_class"
    )
    serializer_class = PromotionBatchSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self) -> list[Any]:
        return [IsAuthenticated(), CanManageStudents()]

    @extend_schema(summary="Preview a promotion batch", tags=["Students - Promotions"])
    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request: Request) -> Response:
        serializer = PromotionPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        institution = _get_request_institution(request)

        batch = preview_promotion(
            institution_id=institution.id,
            from_session_id=data["from_session_id"],
            to_session_id=data["to_session_id"],
            from_class_id=data["from_class_id"],
            to_class_id=data["to_class_id"],
            default_target_section_id=data.get("default_target_section_id"),
            passing_gpa_threshold=data.get("passing_gpa_threshold"),
            student_overrides=data.get("student_overrides"),
        )

        return Response(PromotionBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Apply a previewed promotion batch", tags=["Students - Promotions"])
    @action(detail=True, methods=["post"], url_path="apply")
    def apply(self, request: Request, pk: str | None = None) -> Response:
        batch = self.get_object()
        user = request.user if request.user.is_authenticated else None
        applied_batch = apply_promotion(batch_id=batch.id, applied_by=user)
        return Response(PromotionBatchSerializer(applied_batch).data, status=status.HTTP_200_OK)

    @extend_schema(summary="Rollback an applied promotion batch", tags=["Students - Promotions"])
    @action(detail=True, methods=["post"], url_path="rollback")
    def rollback(self, request: Request, pk: str | None = None) -> Response:
        batch = self.get_object()
        user = request.user if request.user.is_authenticated else None
        rolled_back = rollback_promotion(batch_id=batch.id, user=user)
        return Response(PromotionBatchSerializer(rolled_back).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List transfer certificates", tags=["Students - Transfer Certificates"]
    ),
    retrieve=extend_schema(
        summary="Retrieve transfer certificate", tags=["Students - Transfer Certificates"]
    ),
)
class TransferCertificateViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Transfer certificate issuance and retrieval."""

    queryset = TransferCertificate.objects.all().select_related("student", "enrollment")
    serializer_class = TransferCertificateSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self) -> list[Any]:
        return [IsAuthenticated(), CanManageStudents()]

    @extend_schema(summary="Issue Transfer Certificate", tags=["Students - Transfer Certificates"])
    @action(detail=False, methods=["post"], url_path="issue")
    def issue(self, request: Request) -> Response:
        serializer = IssueTCSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None

        tc = issue_transfer_certificate(
            student_id=data["student_id"],
            reason=data["reason"],
            conduct_remarks=data.get("conduct_remarks", "Satisfactory"),
            dues_cleared=data.get("dues_cleared", True),
            approved_by=user,
        )

        return Response(TransferCertificateSerializer(tc).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Download TC PDF", tags=["Students - Transfer Certificates"])
    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        tc = self.get_object()
        if not tc.pdf_file:
            raise ValidationError("TC PDF not generated.")
        response = HttpResponse(tc.pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{tc.tc_number}.pdf"'
        return response


@extend_schema_view(
    list=extend_schema(summary="List testimonials", tags=["Students - Testimonials"]),
    retrieve=extend_schema(summary="Retrieve testimonial", tags=["Students - Testimonials"]),
)
class TestimonialViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Testimonial / Character Certificate management."""

    queryset = Testimonial.objects.all().select_related("student", "enrollment")
    serializer_class = TestimonialSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self) -> list[Any]:
        return [IsAuthenticated(), CanManageStudents()]

    @extend_schema(summary="Issue Testimonial", tags=["Students - Testimonials"])
    @action(detail=False, methods=["post"], url_path="issue")
    def issue(self, request: Request) -> Response:
        serializer = IssueTestimonialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None

        testimonial = issue_testimonial(
            student_id=data["student_id"],
            exam_name=data["exam_name"],
            passing_year=data["passing_year"],
            gpa=data["gpa"],
            character=data.get("character", "Good"),
            approved_by=user,
        )

        return Response(TestimonialSerializer(testimonial).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Download Testimonial PDF", tags=["Students - Testimonials"])
    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        testimonial = self.get_object()
        if not testimonial.pdf_file:
            raise ValidationError("Testimonial PDF not generated.")
        response = HttpResponse(testimonial.pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{testimonial.certificate_no}.pdf"'
        return response
