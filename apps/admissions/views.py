"""Views and ViewSets for Admission campaigns, applications, tests, and merit lists."""

from typing import Any

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.models import User
from apps.accounts.permissions import HasModulePermission
from apps.admissions.models import (
    AdmissionCircular,
    AdmissionTest,
    AdmissionTestResult,
    Application,
    ApplicationDocument,
    ApplicationPayment,
    ApplicationStatus,
    CircularStatus,
    LotteryDraw,
    MeritList,
    PaymentStatus,
    QuotaRule,
)
from apps.admissions.serializers import (
    AdmissionCircularPublicSerializer,
    AdmissionCircularSerializer,
    AdmissionTestResultSerializer,
    AdmissionTestSerializer,
    ApplicationCreatePublicSerializer,
    ApplicationDocumentSerializer,
    ApplicationPaymentSerializer,
    ApplicationSerializer,
    ApplicationTrackInputSerializer,
    ApplicationTransitionSerializer,
    LotteryDrawInputSerializer,
    LotteryDrawSerializer,
    MeritListGenerateInputSerializer,
    MeritListSerializer,
    QuotaRuleSerializer,
)
from apps.admissions.services.application_workflow import (
    submit_application,
    transition_application_status,
)
from apps.admissions.services.lottery import conduct_lottery_draw
from apps.admissions.services.merit_calculator import generate_merit_list
from apps.admissions.services.student_converter import convert_admitted_application_to_student
from apps.core.mixins import TenantScopedMixin
from apps.core.pagination import StandardResultsSetPagination
from apps.institutions.models import Institution


def get_request_institution(request: Request) -> Institution:
    """Helper to extract and type-narrow the user's institution."""
    user = request.user
    if not isinstance(user, User) or not user.institution:
        raise PermissionDenied("User is not associated with an institution.")
    return user.institution


# --------------------------------------------------------------------------
# Public Admissions API (For Applicants / Guardians)
# --------------------------------------------------------------------------


@extend_schema(tags=["Admissions Public"])
class PublicCircularListView(APIView):
    """Public endpoint to list published, open admission circulars."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="List active admission circulars",
        parameters=[
            OpenApiParameter("institution_id", str, description="Filter by school UUID"),
        ],
        responses={200: AdmissionCircularPublicSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = AdmissionCircular.objects.filter(status=CircularStatus.PUBLISHED).select_related(
            "session", "class_level"
        )
        inst_id = request.query_params.get("institution_id")
        if inst_id:
            qs = qs.filter(institution_id=inst_id)

        serializer = AdmissionCircularPublicSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Admissions Public"])
class PublicApplicationApplyView(APIView):
    """Public endpoint for submitting an admission application."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Submit online admission application",
        request=ApplicationCreatePublicSerializer,
        responses={201: ApplicationSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ApplicationCreatePublicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        output_serializer = ApplicationSerializer(application)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Admissions Public"])
class PublicApplicationTrackView(APIView):
    """Track application status by application number and guardian phone."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Track admission application status",
        request=ApplicationTrackInputSerializer,
        responses={200: ApplicationSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ApplicationTrackInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app_no = serializer.validated_data["application_no"].strip()
        phone = serializer.validated_data["guardian_phone"]

        app = (
            Application.objects.filter(application_no__iexact=app_no, guardian_phone=phone)
            .select_related("circular", "circular__class_level", "circular__session")
            .prefetch_related("documents", "payments")
            .first()
        )
        if not app:
            raise NotFound("No matching application found for this application number and phone.")

        output_serializer = ApplicationSerializer(app)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Admissions Public"])
class PublicAdmitCardView(APIView):
    """Get printable digital admit card details for scheduled admission tests."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get digital admit card data",
        parameters=[
            OpenApiParameter("guardian_phone", str, description="Guardian phone for verification"),
        ],
        responses={200: dict},
    )
    def get(self, request: Request, application_no: str) -> Response:
        phone = request.query_params.get("guardian_phone")
        if not phone:
            raise ValidationError(
                {"guardian_phone": "Guardian phone is required for admit card verification."}
            )

        app = (
            Application.objects.filter(application_no__iexact=application_no, guardian_phone=phone)
            .select_related("circular", "circular__class_level", "institution")
            .first()
        )
        if not app:
            raise NotFound("Application not found or verification phone did not match.")

        test = AdmissionTest.objects.filter(circular=app.circular).first()
        admit_card_data = {
            "institution_name": app.institution.name_en,
            "application_no": app.application_no,
            "applicant_name_en": app.name_en,
            "applicant_name_bn": app.name_bn,
            "class_level": app.circular.class_level.name,
            "dob": str(app.dob),
            "gender": app.gender,
            "test_title": test.title if test else "Admission Assessment",
            "test_date": test.test_date.isoformat() if test else None,
            "venue": test.venue if test else "School Main Campus",
            "instructions": test.instructions if test else app.circular.instructions,
            "status": app.status,
            "photo_url": app.photo.url if app.photo else None,
        }
        return Response(admit_card_data, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------
# Administrative Endpoints (Tenant-Scoped & Permission-Guarded)
# --------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(summary="List admission circulars", tags=["Admissions"]),
    create=extend_schema(summary="Create admission circular", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get circular details", tags=["Admissions"]),
    update=extend_schema(summary="Update admission circular", tags=["Admissions"]),
    partial_update=extend_schema(
        summary="Partially update admission circular", tags=["Admissions"]
    ),
    destroy=extend_schema(summary="Delete admission circular", tags=["Admissions"]),
)
class AdmissionCircularViewSet(TenantScopedMixin, ModelViewSet):
    queryset = AdmissionCircular.objects.select_related("session", "class_level").all()
    serializer_class = AdmissionCircularSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("admissions.view_admissioncircular")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["session", "class_level", "status"]
    search_fields = ["title"]
    ordering_fields = ["form_open_date", "form_close_date"]
    ordering = ["-form_open_date"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))

    @extend_schema(
        summary="Publish admission circular",
        responses={200: AdmissionCircularSerializer},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request: Request, pk: str | None = None) -> Response:
        circular = self.get_object()
        circular.status = CircularStatus.PUBLISHED
        circular.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(circular).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Close admission circular",
        responses={200: AdmissionCircularSerializer},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request: Request, pk: str | None = None) -> Response:
        circular = self.get_object()
        circular.status = CircularStatus.CLOSED
        circular.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(circular).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List quota rules", tags=["Admissions"]),
    create=extend_schema(summary="Create quota rule", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get quota rule details", tags=["Admissions"]),
    update=extend_schema(summary="Update quota rule", tags=["Admissions"]),
    partial_update=extend_schema(summary="Partially update quota rule", tags=["Admissions"]),
    destroy=extend_schema(summary="Delete quota rule", tags=["Admissions"]),
)
class QuotaRuleViewSet(TenantScopedMixin, ModelViewSet):
    queryset = QuotaRule.objects.select_related("circular").all()
    serializer_class = QuotaRuleSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("admissions.view_quotarule")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["circular", "quota_type"]
    ordering_fields = ["priority"]
    ordering = ["priority"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List admission applications", tags=["Admissions"]),
    create=extend_schema(summary="Create admission application (admin)", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get application details", tags=["Admissions"]),
    update=extend_schema(summary="Update admission application", tags=["Admissions"]),
    partial_update=extend_schema(summary="Partially update application", tags=["Admissions"]),
    destroy=extend_schema(summary="Delete application", tags=["Admissions"]),
)
class ApplicationViewSet(TenantScopedMixin, ModelViewSet):
    queryset = (
        Application.objects.select_related(
            "circular", "circular__class_level", "circular__session", "quota_rule"
        )
        .prefetch_related("documents", "payments")
        .all()
    )
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("admissions.view_application")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["circular", "status", "quota_type", "gender"]
    search_fields = ["application_no", "name_en", "name_bn", "guardian_phone", "birth_reg_no"]
    ordering_fields = ["created_at", "application_no", "name_en"]
    ordering = ["-created_at"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))

    @extend_schema(
        summary="Transition application lifecycle status",
        request=ApplicationTransitionSerializer,
        responses={200: ApplicationSerializer},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request: Request, pk: str | None = None) -> Response:
        application = self.get_object()
        serializer = ApplicationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_app = transition_application_status(
            application=application,
            new_status=serializer.validated_data["new_status"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(self.get_serializer(updated_app).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit application",
        responses={200: ApplicationSerializer},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request: Request, pk: str | None = None) -> Response:
        app = self.get_object()
        updated_app = submit_application(app.id)
        return Response(self.get_serializer(updated_app).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Convert admitted application into permanent student profile (Task 06 stub)",
        responses={200: dict},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="convert-to-student")
    def convert_to_student(self, request: Request, pk: str | None = None) -> Response:
        app = self.get_object()
        result = convert_admitted_application_to_student(app.id)
        return Response(result, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List application documents", tags=["Admissions"]),
    create=extend_schema(summary="Upload application document", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get document details", tags=["Admissions"]),
    destroy=extend_schema(summary="Delete application document", tags=["Admissions"]),
)
class ApplicationDocumentViewSet(TenantScopedMixin, ModelViewSet):
    queryset = ApplicationDocument.objects.select_related("application").all()
    serializer_class = ApplicationDocumentSerializer
    permission_classes = [
        IsAuthenticated,
        HasModulePermission("admissions.view_applicationdocument"),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["application", "is_verified", "document_type"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))

    @extend_schema(
        summary="Mark application document as verified",
        responses={200: ApplicationDocumentSerializer},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request: Request, pk: str | None = None) -> Response:
        doc = self.get_object()
        doc.is_verified = True
        doc.verified_at = timezone.now()
        doc.save(update_fields=["is_verified", "verified_at", "updated_at"])
        return Response(self.get_serializer(doc).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List admission payments", tags=["Admissions"]),
    create=extend_schema(summary="Record admission payment", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get payment details", tags=["Admissions"]),
)
class ApplicationPaymentViewSet(TenantScopedMixin, ModelViewSet):
    queryset = ApplicationPayment.objects.select_related("application").all()
    serializer_class = ApplicationPaymentSerializer
    permission_classes = [
        IsAuthenticated,
        HasModulePermission("admissions.view_applicationpayment"),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["application", "status", "payment_method"]
    search_fields = ["transaction_id"]

    def perform_create(self, serializer: Any) -> None:
        payment = serializer.save(institution=get_request_institution(self.request))
        if (
            payment.status == PaymentStatus.COMPLETED
            and payment.application.status == ApplicationStatus.SUBMITTED
        ):
            transition_application_status(
                application=payment.application,
                new_status=ApplicationStatus.PAID,
                notes=f"Payment received: ৳{payment.amount} ({payment.payment_method})",
            )


@extend_schema_view(
    list=extend_schema(summary="List admission tests", tags=["Admissions"]),
    create=extend_schema(summary="Schedule an admission test", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get test details", tags=["Admissions"]),
    update=extend_schema(summary="Update admission test", tags=["Admissions"]),
    destroy=extend_schema(summary="Delete admission test", tags=["Admissions"]),
)
class AdmissionTestViewSet(TenantScopedMixin, ModelViewSet):
    queryset = AdmissionTest.objects.select_related("circular").all()
    serializer_class = AdmissionTestSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("admissions.view_admissiontest")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["circular"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List test results", tags=["Admissions"]),
    create=extend_schema(summary="Record test score", tags=["Admissions"]),
    retrieve=extend_schema(summary="Get test score details", tags=["Admissions"]),
    update=extend_schema(summary="Update test score", tags=["Admissions"]),
)
class AdmissionTestResultViewSet(TenantScopedMixin, ModelViewSet):
    queryset = AdmissionTestResult.objects.select_related("test", "application").all()
    serializer_class = AdmissionTestResultSerializer
    permission_classes = [
        IsAuthenticated,
        HasModulePermission("admissions.view_admissiontestresult"),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["test", "application", "is_passed"]
    ordering_fields = ["marks_obtained"]
    ordering = ["-marks_obtained"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(institution=get_request_institution(self.request))


@extend_schema_view(
    list=extend_schema(summary="List lottery draws", tags=["Admissions"]),
    retrieve=extend_schema(
        summary="Get lottery draw details and candidate sequence", tags=["Admissions"]
    ),
)
class LotteryDrawViewSet(TenantScopedMixin, ReadOnlyModelViewSet):
    queryset = LotteryDraw.objects.select_related("circular").all()
    serializer_class = LotteryDrawSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("admissions.view_lotterydraw")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["circular", "is_confirmed"]

    @extend_schema(
        summary="Conduct deterministic lottery draw",
        request=LotteryDrawInputSerializer,
        responses={201: LotteryDrawSerializer},
        tags=["Admissions"],
    )
    @action(detail=False, methods=["post"], url_path="draw")
    def draw(self, request: Request) -> Response:
        serializer = LotteryDrawInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        draw = conduct_lottery_draw(
            circular_id=data["circular_id"],
            total_to_select=data["total_to_select"],
            seed=data.get("seed"),
            conducted_by_user=request.user,
            auto_advance_status=data.get("auto_advance_status", False),
        )
        return Response(LotteryDrawSerializer(draw).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(summary="List merit lists", tags=["Admissions"]),
    retrieve=extend_schema(
        summary="Get merit list and ranked candidate entries", tags=["Admissions"]
    ),
)
class MeritListViewSet(TenantScopedMixin, ReadOnlyModelViewSet):
    queryset = (
        MeritList.objects.select_related("circular")
        .prefetch_related("entries", "entries__application")
        .all()
    )
    serializer_class = MeritListSerializer
    permission_classes = [IsAuthenticated, HasModulePermission("admissions.view_meritlist")]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["circular", "is_published", "selection_criteria"]

    @extend_schema(
        summary="Generate merit list with quota allocations",
        request=MeritListGenerateInputSerializer,
        responses={201: MeritListSerializer},
        tags=["Admissions"],
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request: Request) -> Response:
        serializer = MeritListGenerateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        merit_list = generate_merit_list(
            circular_id=data["circular_id"],
            selection_criteria=data["selection_criteria"],
            title=data.get("title", "1st Merit List"),
            auto_publish=data.get("auto_publish", False),
        )
        return Response(MeritListSerializer(merit_list).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Publish merit list",
        responses={200: MeritListSerializer},
        tags=["Admissions"],
    )
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request: Request, pk: str | None = None) -> Response:
        merit_list = self.get_object()
        merit_list.is_published = True
        merit_list.published_at = timezone.now()
        merit_list.save(update_fields=["is_published", "published_at", "updated_at"])
        return Response(self.get_serializer(merit_list).data, status=status.HTTP_200_OK)
