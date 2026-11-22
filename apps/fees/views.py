"""REST API ViewSets for fee structures, invoices, waivers, and fines."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import ClassLevel
from apps.accounts.models import User
from apps.fees.gateways import get_gateway_adapter
from apps.fees.models import (
    AdvanceBalance,
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FineRule,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    MoneyReceipt,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Refund,
    StudentFeeAssignment,
    StudentWaiver,
    WaiverRule,
)
from apps.fees.permissions import (
    CanApproveWaiver,
    CanGenerateInvoices,
    CanManageFees,
    CanViewFees,
    CanViewInvoiceDetail,
)
from apps.fees.serializers import (
    AdvanceBalanceSerializer,
    ApplyAdvanceSerializer,
    CounterPaymentSerializer,
    DailyCollectionReportSerializer,
    DueListItemSerializer,
    FeeHeadSerializer,
    FeeStructureItemSerializer,
    FeeStructureSerializer,
    FineRuleSerializer,
    InvoiceBulkGenerateResponseSerializer,
    InvoiceBulkGenerateSerializer,
    InvoiceBulkPreviewResponseSerializer,
    InvoiceBulkPreviewSerializer,
    InvoiceCancelSerializer,
    InvoiceDetailSerializer,
    InvoiceSerializer,
    InvoiceSingleGenerateSerializer,
    MoneyReceiptSerializer,
    OnlinePaymentInitiateResponseSerializer,
    OnlinePaymentInitiateSerializer,
    OnlinePaymentVerifySerializer,
    PaymentDetailSerializer,
    PaymentSerializer,
    RefundCreateSerializer,
    RefundRejectSerializer,
    RefundSerializer,
    StudentFeeAssignmentSerializer,
    StudentWaiverSerializer,
    WaiverRejectSerializer,
    WaiverRuleSerializer,
)
from apps.fees.services import (
    apply_advance_to_invoice,
    approve_refund,
    approve_student_waiver,
    cancel_invoice,
    complete_online_payment,
    generate_bulk_invoices,
    generate_invoice_pdf,
    generate_money_receipt_pdf,
    generate_single_student_invoice,
    initiate_online_payment,
    issue_invoice,
    preview_bulk_invoices,
    process_refund,
    record_counter_payment,
    reject_refund,
    reject_student_waiver,
    request_refund,
)
from apps.institutions.models import AcademicSession
from apps.students.models import Student


@extend_schema_view(
    list=extend_schema(summary="List all fee heads for the institution"),
    retrieve=extend_schema(summary="Retrieve fee head details"),
    create=extend_schema(summary="Create a new fee head"),
    update=extend_schema(summary="Update a fee head"),
    destroy=extend_schema(summary="Soft delete a fee head"),
)
class FeeHeadViewSet(viewsets.ModelViewSet):
    """Institutional categories of fees (Tuition, Admission, Exam, Transport, etc.)."""

    queryset = FeeHead.objects.filter(is_deleted=False)
    serializer_class = FeeHeadSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["fee_type", "recurrence", "is_optional", "is_refundable", "is_active"]
    search_fields = ["code", "name_en", "name_bn"]
    ordering_fields = ["code", "name_en", "created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanManageFees()]
        return [IsAuthenticated(), CanViewFees()]

    def perform_create(self, serializer: Any) -> None:
        inst = getattr(self.request.user, "institution", None)
        serializer.save(institution=inst)

    def perform_destroy(self, instance: FeeHead) -> None:
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])


@extend_schema_view(
    list=extend_schema(summary="List class fee structure templates"),
    retrieve=extend_schema(summary="Retrieve fee structure template with items"),
    create=extend_schema(summary="Create a new class fee structure"),
    update=extend_schema(summary="Update a fee structure"),
    destroy=extend_schema(summary="Soft delete a fee structure"),
)
class FeeStructureViewSet(viewsets.ModelViewSet):
    """Grade and session fee structures aggregating fee items."""

    queryset = FeeStructure.objects.filter(is_deleted=False).prefetch_related("items__fee_head")
    serializer_class = FeeStructureSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["session", "class_level", "is_active"]
    search_fields = ["name", "class_level__name"]

    def get_permissions(self) -> list[Any]:
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "add_item",
            "remove_item",
        ]:
            return [IsAuthenticated(), CanManageFees()]
        return [IsAuthenticated(), CanViewFees()]

    def perform_create(self, serializer: Any) -> None:
        inst = getattr(self.request.user, "institution", None)
        serializer.save(institution=inst)

    def perform_destroy(self, instance: FeeStructure) -> None:
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])

    @extend_schema(
        summary="Add a fee item to an existing fee structure",
        request=FeeStructureItemSerializer,
        responses={201: FeeStructureItemSerializer},
    )
    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request: Request, pk: str | None = None) -> Response:
        structure = self.get_object()
        serializer = FeeStructureItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(fee_structure=structure, institution=structure.institution)
        return Response(FeeStructureItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove a fee item from a fee structure",
        parameters=[
            OpenApiParameter("item_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=True)
        ],
    )
    @action(detail=True, methods=["delete"], url_path="items")
    def remove_item(self, request: Request, pk: str | None = None) -> Response:
        structure = self.get_object()
        item_id = request.query_params.get("item_id")
        if not item_id:
            raise ValidationError({"item_id": "item_id query parameter is required."})
        item = FeeStructureItem.objects.filter(id=item_id, fee_structure=structure).first()
        if not item:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudentFeeAssignmentViewSet(viewsets.ModelViewSet):
    """Personalized student fee overrides and exemptions."""

    queryset = StudentFeeAssignment.objects.filter(is_deleted=False).select_related(
        "student", "fee_head"
    )
    serializer_class = StudentFeeAssignmentSerializer
    permission_classes = [IsAuthenticated, CanManageFees]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["student", "fee_head", "is_exempt"]
    search_fields = ["student__student_id", "student__name_en", "fee_head__name_en"]

    def perform_create(self, serializer: Any) -> None:
        inst = getattr(self.request.user, "institution", None)
        serializer.save(institution=inst)


class WaiverRuleViewSet(viewsets.ModelViewSet):
    """Institutional discount/scholarship rules."""

    queryset = WaiverRule.objects.filter(is_deleted=False).prefetch_related("applicable_fee_heads")
    serializer_class = WaiverRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category", "discount_type", "is_active"]
    search_fields = ["name", "description"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanManageFees()]
        return [IsAuthenticated(), CanViewFees()]

    def perform_create(self, serializer: Any) -> None:
        inst = getattr(self.request.user, "institution", None)
        serializer.save(institution=inst)


class StudentWaiverViewSet(viewsets.ModelViewSet):
    """Student waiver allocations with approval workflow."""

    queryset = StudentWaiver.objects.filter(is_deleted=False).select_related(
        "student", "waiver_rule", "approved_by"
    )
    serializer_class = StudentWaiverSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["student", "status", "discount_type"]
    search_fields = ["student__student_id", "student__name_en", "title"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["approve", "reject"]:
            return [IsAuthenticated(), CanApproveWaiver()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanManageFees()]
        return [IsAuthenticated(), CanViewFees()]

    def perform_create(self, serializer: Any) -> None:
        inst = getattr(self.request.user, "institution", None)
        serializer.save(institution=inst)

    @extend_schema(
        summary="Approve a pending student waiver",
        request=None,
        responses={200: StudentWaiverSerializer},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        waiver = self.get_object()
        assert isinstance(request.user, User)
        approved = approve_student_waiver(waiver_id=waiver.id, approver=request.user)
        return Response(StudentWaiverSerializer(approved).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Reject a student waiver with a reason",
        request=WaiverRejectSerializer,
        responses={200: StudentWaiverSerializer},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        waiver = self.get_object()
        ser = WaiverRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assert isinstance(request.user, User)
        rejected = reject_student_waiver(
            waiver_id=waiver.id,
            approver=request.user,
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(StudentWaiverSerializer(rejected).data, status=status.HTTP_200_OK)


class FineRuleViewSet(viewsets.ModelViewSet):
    """Institutional late payment fine policies."""

    queryset = FineRule.objects.filter(is_deleted=False)
    serializer_class = FineRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["fine_type", "is_active"]
    search_fields = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanManageFees()]
        return [IsAuthenticated(), CanViewFees()]

    def perform_create(self, serializer: Any) -> None:
        inst = getattr(self.request.user, "institution", None)
        serializer.save(institution=inst)


class InvoiceViewSet(viewsets.ModelViewSet):
    """Comprehensive invoice lifecycle management and generation."""

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "student",
        "session",
        "invoice_type",
        "billing_month",
        "billing_year",
        "status",
    ]
    search_fields = ["invoice_number", "student__student_id", "student__name_en", "title"]
    ordering_fields = ["issue_date", "due_date", "invoice_number", "total_payable"]

    def get_serializer_class(self) -> type[serializers.ModelSerializer]:
        if self.action == "retrieve":
            return InvoiceDetailSerializer
        return InvoiceSerializer

    def get_permissions(self) -> list[Any]:
        if self.action in ["generate_single", "bulk_preview", "bulk_generate", "issue", "cancel"]:
            return [IsAuthenticated(), CanGenerateInvoices()]
        return [IsAuthenticated(), CanViewInvoiceDetail()]

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = (
            Invoice.objects.filter(is_deleted=False)
            .select_related("student", "enrollment", "session")
            .prefetch_related("lines__fee_head")
        )

        if not user or not user.is_authenticated:
            return qs.none()

        if user.is_superuser:
            return qs

        # Staff with fees.view can view all for tenant
        if CanViewFees().has_permission(self.request, self):
            return qs

        # Guardians can view their wards' invoices
        guardians = list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
        if guardians:
            wards = []
            for g in guardians:
                if hasattr(g, "students"):
                    wards.extend(list(g.students.values_list("id", flat=True)))
            return qs.filter(student_id__in=wards).exclude(status=InvoiceStatus.DRAFT)

        return qs.none()

    @extend_schema(
        summary="Generate a single invoice for a student",
        request=InvoiceSingleGenerateSerializer,
        responses={201: InvoiceDetailSerializer},
    )
    @action(detail=False, methods=["post"], url_path="generate-single")
    def generate_single(self, request: Request) -> Response:
        ser = InvoiceSingleGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        student = Student.objects.get(id=d["student_id"])
        session = AcademicSession.objects.get(id=d["session_id"])
        fee_structure = None
        if d.get("fee_structure_id"):
            fee_structure = FeeStructure.objects.get(id=d["fee_structure_id"])

        inv = generate_single_student_invoice(
            student=student,
            session=session,
            invoice_type=d.get("invoice_type", InvoiceType.MONTHLY),
            billing_year=d.get("billing_year", 2026),
            billing_month=d.get("billing_month"),
            fee_structure=fee_structure,
            issue_date=d.get("issue_date"),
            due_date=d.get("due_date"),
            title=d.get("title", ""),
            as_issued=d.get("as_issued", True),
        )
        return Response(InvoiceDetailSerializer(inv).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Preview bulk invoice generation parameters & deduplication counts",
        request=InvoiceBulkPreviewSerializer,
        responses={200: InvoiceBulkPreviewResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="bulk-preview")
    def bulk_preview(self, request: Request) -> Response:
        ser = InvoiceBulkPreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        session = AcademicSession.objects.get(id=d["session_id"])
        class_level = ClassLevel.objects.get(id=d["class_level_id"])

        res = preview_bulk_invoices(
            institution=session.institution,
            session=session,
            class_level=class_level,
            section_id=d.get("section_id"),
            billing_month=d.get("billing_month"),
            billing_year=d.get("billing_year", 2026),
            invoice_type=d.get("invoice_type", InvoiceType.MONTHLY),
        )
        return Response(res, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Execute bulk invoice generation for a class or section",
        request=InvoiceBulkGenerateSerializer,
        responses={201: InvoiceBulkGenerateResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="bulk-generate")
    def bulk_generate(self, request: Request) -> Response:
        ser = InvoiceBulkGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        session = AcademicSession.objects.get(id=d["session_id"])
        class_level = ClassLevel.objects.get(id=d["class_level_id"])

        res = generate_bulk_invoices(
            institution=session.institution,
            session=session,
            class_level=class_level,
            section_id=d.get("section_id"),
            billing_month=d.get("billing_month"),
            billing_year=d.get("billing_year", 2026),
            invoice_type=d.get("invoice_type", InvoiceType.MONTHLY),
            issue_date=d.get("issue_date"),
            due_date=d.get("due_date"),
            as_issued=d.get("as_issued", True),
        )
        return Response(res, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Transition draft invoice to issued status",
        request=None,
        responses={200: InvoiceSerializer},
    )
    @action(detail=True, methods=["post"])
    def issue(self, request: Request, pk: str | None = None) -> Response:
        inv = self.get_object()
        issued = issue_invoice(inv)
        return Response(InvoiceSerializer(issued).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Cancel an invoice with mandatory audit reason",
        request=InvoiceCancelSerializer,
        responses={200: InvoiceSerializer},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        inv = self.get_object()
        ser = InvoiceCancelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cancelled = cancel_invoice(inv, reason=ser.validated_data["reason"])
        return Response(InvoiceSerializer(cancelled).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Download bilingual invoice / payment demand slip PDF",
        responses={(200, "application/pdf"): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=["get"])
    def pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        inv = self.get_object()
        pdf_bytes = generate_invoice_pdf(inv)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{inv.invoice_number}.pdf"'
        return response


class DueListView(APIView):
    """Query list of students with outstanding dues and defaulter metrics."""

    permission_classes = [IsAuthenticated, CanViewFees]

    @extend_schema(
        summary="List students with overdue or pending fees",
        parameters=[
            OpenApiParameter(
                "class_level_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                "section_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter("min_due", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: DueListItemSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        inst = getattr(request.user, "institution", None)
        class_id = request.query_params.get("class_level_id")
        section_id = request.query_params.get("section_id")
        min_due_param = request.query_params.get("min_due", "1.00")
        try:
            min_due = Decimal(min_due_param)
        except Exception:
            min_due = Decimal("1.00")

        invoices = (
            Invoice.objects.filter(
                status__in=[
                    InvoiceStatus.ISSUED,
                    InvoiceStatus.OVERDUE,
                    InvoiceStatus.PARTIALLY_PAID,
                ],
                due_amount__gte=min_due,
                is_deleted=False,
            )
            .select_related("student", "enrollment__class_level", "enrollment__section")
            .order_by("student_id")
        )

        if inst:
            invoices = invoices.filter(institution=inst)
        if class_id:
            try:
                invoices = invoices.filter(enrollment__class_level_id=UUID(class_id))
            except (ValueError, TypeError):
                invoices = invoices.none()
        if section_id:
            try:
                invoices = invoices.filter(enrollment__section_id=UUID(section_id))
            except (ValueError, TypeError):
                invoices = invoices.none()

        # Aggregate by student
        student_map: dict[str, dict[str, Any]] = {}
        for inv in invoices:
            sid = str(inv.student.id)
            if sid not in student_map:
                enr = inv.enrollment
                c_name = enr.class_level.name if (enr and enr.class_level) else "N/A"
                s_name = enr.section.name if (enr and enr.section) else "N/A"
                r_no = enr.roll_no if enr else None

                student_map[sid] = {
                    "student_id": inv.student.student_id,
                    "student_name_en": inv.student.name_en,
                    "student_name_bn": inv.student.name_bn,
                    "roll_no": r_no,
                    "class_name": c_name,
                    "section_name": s_name,
                    "unpaid_invoice_count": 0,
                    "total_due_amount": Decimal("0.00"),
                    "oldest_overdue_date": inv.due_date,
                }

            student_map[sid]["unpaid_invoice_count"] += 1
            student_map[sid]["total_due_amount"] += inv.due_amount
            if inv.due_date < student_map[sid]["oldest_overdue_date"]:
                student_map[sid]["oldest_overdue_date"] = inv.due_date

        return Response(list(student_map.values()), status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List all payments"),
    retrieve=extend_schema(summary="Retrieve payment details including line item allocations"),
)
class PaymentViewSet(viewsets.ModelViewSet):
    """Payment records for counter collections and online gateways."""

    queryset = (
        Payment.objects.filter(is_deleted=False)
        .select_related("student", "invoice", "received_by", "receipt")
        .prefetch_related("allocations__invoice_line__fee_head")
    )
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["payment_method", "status", "student", "invoice"]
    search_fields = [
        "transaction_id",
        "gateway_order_id",
        "student__student_id",
        "student__name_en",
        "idempotency_key",
    ]
    ordering_fields = ["payment_date", "amount", "created_at"]

    def get_serializer_class(self) -> Any:
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return PaymentSerializer

    def get_permissions(self) -> list[Any]:
        if self.action == "webhook":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = super().get_queryset()
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser or CanViewFees().has_permission(self.request, self):
            return qs
        guardians = list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
        if guardians:
            wards = []
            for g in guardians:
                if hasattr(g, "students"):
                    wards.extend(list(g.students.values_list("id", flat=True)))
            return qs.filter(student_id__in=wards)
        return qs.none()

    @extend_schema(
        summary="Record a manual counter payment (Cash, Bank, Cheque, POS)",
        request=CounterPaymentSerializer,
        responses={201: PaymentDetailSerializer},
    )
    @action(detail=False, methods=["post"], url_path="counter")
    def counter(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        ser = CounterPaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        student = Student.objects.get(id=d["student_id"])
        invoice = None
        if d.get("invoice_id"):
            invoice = Invoice.objects.get(id=d["invoice_id"])

        payment = record_counter_payment(
            institution=student.institution,
            collected_by=request.user,
            student=student,
            amount=d["amount"],
            payment_method=d.get("payment_method", PaymentMethod.CASH),
            invoice=invoice,
            idempotency_key=d.get("idempotency_key") or None,
            bank_name=d.get("bank_name", ""),
            cheque_no=d.get("cheque_no", ""),
            cheque_date=d.get("cheque_date"),
            pos_approval_code=d.get("pos_approval_code", ""),
            notes=d.get("notes", ""),
        )
        return Response(PaymentDetailSerializer(payment).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Initiate an online payment session (bKash, Nagad, SSLCommerz, aamarPay)",
        request=OnlinePaymentInitiateSerializer,
        responses={200: OnlinePaymentInitiateResponseSerializer},
    )
    @action(detail=False, methods=["post"], url_path="initiate-online")
    def initiate_online(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        ser = OnlinePaymentInitiateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        invoice = Invoice.objects.get(id=d["invoice_id"])
        urls = {
            "success_url": d.get("success_url", ""),
            "fail_url": d.get("fail_url", ""),
            "cancel_url": d.get("cancel_url", ""),
        }
        res = initiate_online_payment(
            invoice=invoice,
            payment_method=d["payment_method"],
            urls=urls,
            payer_user=request.user,
        )
        return Response(
            OnlinePaymentInitiateResponseSerializer(res).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Verify and finalize an online payment transaction",
        request=OnlinePaymentVerifySerializer,
        responses={200: PaymentDetailSerializer},
    )
    @action(detail=False, methods=["post"], url_path="verify")
    def verify(self, request: Request) -> Response:
        ser = OnlinePaymentVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        payment = Payment.objects.get(id=d["payment_id"])
        completed_payment = complete_online_payment(payment, verification_params=d)
        return Response(PaymentDetailSerializer(completed_payment).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Public gateway webhook / IPN callback",
        parameters=[
            OpenApiParameter(
                name="gateway",
                type=str,
                location=OpenApiParameter.PATH,
                description="Gateway identifier (sslcommerz, bkash, nagad, aamarpay)",
            )
        ],
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"webhook/(?P<gateway>[^/.]+)",
        permission_classes=[AllowAny],
    )
    def webhook(self, request: Request, gateway: str | None = None) -> Response:
        if not gateway:
            return Response({"error": "Gateway not specified"}, status=status.HTTP_400_BAD_REQUEST)

        adapter = get_gateway_adapter(gateway)
        if not adapter.validate_ipn_signature(request.data):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        tran_id = (
            request.data.get("tran_id")
            or request.data.get("mer_txnid")
            or request.data.get("paymentID")
            or request.data.get("order_id")
        )
        payment = None
        if tran_id:
            payment = Payment.objects.filter(
                gateway_order_id=tran_id,
                status__in=[PaymentStatus.INITIATED, PaymentStatus.PENDING],
            ).first()

        if not payment:
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        complete_online_payment(payment, verification_params=request.data)
        return Response({"status": "accepted"}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Daily collection report grouped by payment method",
        parameters=[
            OpenApiParameter(name="date", type=str, description="YYYY-MM-DD (defaults to today)"),
        ],
        responses={200: DailyCollectionReportSerializer},
    )
    @action(detail=False, methods=["get"], url_path="daily-collection")
    def daily_collection(self, request: Request) -> Response:
        date_str = request.query_params.get("date")
        target_date = parse_date(date_str) if date_str else timezone.now().date()
        if not target_date:
            target_date = timezone.now().date()

        qs = self.get_queryset().filter(
            status=PaymentStatus.SUCCESSFUL,
            payment_date__date=target_date,
        )

        total_collected = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        payment_count = qs.count()

        by_method_qs = (
            qs.values("payment_method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("payment_method")
        )
        by_method = {
            item["payment_method"]: {
                "total": str(item["total"]),
                "count": item["count"],
            }
            for item in by_method_qs
        }

        report_data = {
            "date": target_date,
            "total_collected": total_collected,
            "payment_count": payment_count,
            "by_method": by_method,
        }
        return Response(
            DailyCollectionReportSerializer(report_data).data, status=status.HTTP_200_OK
        )


@extend_schema_view(
    list=extend_schema(summary="List all issued money receipts"),
    retrieve=extend_schema(summary="Retrieve money receipt details"),
)
class MoneyReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    """Official issued money receipts."""

    queryset = MoneyReceipt.objects.filter(is_deleted=False).select_related(
        "student", "payment", "issued_by"
    )
    serializer_class = MoneyReceiptSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["student", "is_cancelled"]
    search_fields = ["receipt_number", "student__student_id", "student__name_en"]
    ordering_fields = ["issued_at", "total_amount"]

    def get_permissions(self) -> list[Any]:
        return [IsAuthenticated()]

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = super().get_queryset()
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser or CanViewFees().has_permission(self.request, self):
            return qs
        guardians = list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
        if guardians:
            wards = []
            for g in guardians:
                if hasattr(g, "students"):
                    wards.extend(list(g.students.values_list("id", flat=True)))
            return qs.filter(student_id__in=wards)
        return qs.none()

    @extend_schema(summary="Download or view Money Receipt PDF")
    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request: Request, pk: str | None = None) -> HttpResponse:
        receipt = self.get_object()
        pdf_bytes = generate_money_receipt_pdf(receipt)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{receipt.receipt_number}.pdf"'
        return response


@extend_schema_view(
    list=extend_schema(summary="List student advance balances"),
    retrieve=extend_schema(summary="Retrieve student advance balance and transaction ledger"),
)
class AdvanceBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Student advance balances and credit ledgers."""

    queryset = AdvanceBalance.objects.select_related("student").prefetch_related("transactions")
    serializer_class = AdvanceBalanceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["student__student_id", "student__name_en"]
    ordering_fields = ["current_balance", "updated_at"]

    def get_permissions(self) -> list[Any]:
        return [IsAuthenticated()]

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = super().get_queryset()
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser or CanViewFees().has_permission(self.request, self):
            return qs
        guardians = list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
        if guardians:
            wards = []
            for g in guardians:
                if hasattr(g, "students"):
                    wards.extend(list(g.students.values_list("id", flat=True)))
            return qs.filter(student_id__in=wards)
        return qs.none()

    @extend_schema(
        summary="Apply available advance balance to pay an invoice",
        request=ApplyAdvanceSerializer,
        responses={200: AdvanceBalanceSerializer},
    )
    @action(detail=True, methods=["post"], url_path="apply")
    def apply_to_invoice(self, request: Request, pk: str | None = None) -> Response:
        advance = self.get_object()
        ser = ApplyAdvanceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        invoice = Invoice.objects.get(id=d["invoice_id"])
        apply_advance_to_invoice(
            student=advance.student,
            invoice=invoice,
            amount=d["amount"],
        )
        advance.refresh_from_db()
        return Response(AdvanceBalanceSerializer(advance).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List all refund requests"),
    retrieve=extend_schema(summary="Retrieve refund request details"),
)
class RefundViewSet(viewsets.ModelViewSet):
    """Refund requests, approval, and processing workflow."""

    queryset = Refund.objects.filter(is_deleted=False).select_related(
        "payment", "student", "requested_by", "approved_by"
    )
    serializer_class = RefundSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "student", "payment"]
    search_fields = ["student__student_id", "payment__transaction_id", "reason"]
    ordering_fields = ["created_at", "amount"]

    def get_permissions(self) -> list[Any]:
        return [IsAuthenticated()]

    def get_queryset(self) -> Any:
        user = self.request.user
        qs = super().get_queryset()
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser or CanViewFees().has_permission(self.request, self):
            return qs
        guardians = list(user.guardian_profiles.all()) if hasattr(user, "guardian_profiles") else []
        if guardians:
            wards = []
            for g in guardians:
                if hasattr(g, "students"):
                    wards.extend(list(g.students.values_list("id", flat=True)))
            return qs.filter(student_id__in=wards)
        return qs.none()

    @extend_schema(
        summary="Submit a refund request for a completed payment",
        request=RefundCreateSerializer,
        responses={201: RefundSerializer},
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        assert isinstance(request.user, User)
        ser = RefundCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        payment = Payment.objects.get(id=d["payment_id"])
        refund = request_refund(
            payment=payment,
            amount=d["amount"],
            reason=d["reason"],
            requested_by=request.user,
        )
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Approve a pending refund request", responses={200: RefundSerializer})
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request: Request, pk: str | None = None) -> Response:
        assert isinstance(request.user, User)
        refund = self.get_object()
        approved = approve_refund(refund=refund, approved_by=request.user)
        return Response(RefundSerializer(approved).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Reject a pending refund request",
        request=RefundRejectSerializer,
        responses={200: RefundSerializer},
    )
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request: Request, pk: str | None = None) -> Response:
        assert isinstance(request.user, User)
        refund = self.get_object()
        ser = RefundRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        rejected = reject_refund(
            refund=refund,
            rejected_by=request.user,
            rejection_reason=d["rejection_reason"],
        )
        return Response(RefundSerializer(rejected).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Execute and process an approved refund (unwinding invoice allocations)",
        responses={200: RefundSerializer},
    )
    @action(detail=True, methods=["post"], url_path="process")
    def process(self, request: Request, pk: str | None = None) -> Response:
        assert isinstance(request.user, User)
        refund = self.get_object()
        processed = process_refund(refund=refund, processed_by=request.user)
        return Response(RefundSerializer(processed).data, status=status.HTTP_200_OK)
