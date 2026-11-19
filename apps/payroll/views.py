"""DRF Views for Payroll Management, Payslips, Accounting Posting, and Exports."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.mixins import TenantScopedMixin, get_request_institution
from apps.payroll.models import (
    PayrollRun,
    Payslip,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
    StaffLoan,
    StaffSalaryOverride,
    StaffSalaryProfile,
)
from apps.payroll.permissions import (
    CanApprovePayroll,
    CanManagePayroll,
    CanViewPayroll,
    IsPayrollAdminOrSelf,
)
from apps.payroll.serializers import (
    ApplyBonusSerializer,
    GeneratePayrollRunSerializer,
    MarkPaidSerializer,
    PayrollRunSerializer,
    PayslipSerializer,
    PostAccountingSerializer,
    SalaryComponentSerializer,
    SalaryStructureLineSerializer,
    SalaryStructureSerializer,
    StaffLoanSerializer,
    StaffSalaryOverrideSerializer,
    StaffSalaryProfileSerializer,
)
from apps.payroll.services import (
    apply_bonus_to_run,
    approve_payroll_run,
    export_bank_advice_csv,
    export_bank_advice_xlsx,
    generate_payroll_run,
    lock_payroll_run,
    mark_payroll_run_paid,
    post_payroll_to_accounting,
    render_payslip_pdf,
    review_payroll_run,
    seed_default_salary_components,
    seed_default_salary_structures,
)
from apps.staff.models import Staff, StaffStatus


def _raise_drf_validation(exc: DjangoValidationError) -> None:
    """Convert Django model/service ValidationError into a DRF 400 error."""
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise DRFValidationError(detail)


@extend_schema_view(
    list=extend_schema(summary="List salary components", tags=["Payroll - Setup"]),
    retrieve=extend_schema(summary="Retrieve salary component", tags=["Payroll - Setup"]),
    create=extend_schema(summary="Create salary component", tags=["Payroll - Setup"]),
    update=extend_schema(summary="Update salary component", tags=["Payroll - Setup"]),
    partial_update=extend_schema(
        summary="Partial update salary component", tags=["Payroll - Setup"]
    ),
    destroy=extend_schema(summary="Soft-delete salary component", tags=["Payroll - Setup"]),
)
class SalaryComponentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for institutional earning and deduction components."""

    queryset = SalaryComponent.objects.filter(is_deleted=False).order_by(
        "component_type", "display_order", "code"
    )
    serializer_class = SalaryComponentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["component_type", "calculation_type", "is_active"]
    search_fields = ["code", "name_en", "name_bn"]
    ordering_fields = ["display_order", "code", "name_en"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPayroll()]
        return [IsAuthenticated(), CanManagePayroll()]

    def perform_destroy(self, instance: SalaryComponent) -> None:
        if instance.is_system:
            raise DRFValidationError("System salary components cannot be deleted.")
        instance.delete()

    @extend_schema(
        summary="Seed default Bangladeshi salary components",
        tags=["Payroll - Setup"],
        request=None,
        responses={200: SalaryComponentSerializer(many=True)},
    )
    @action(detail=False, methods=["post"])
    def seed_defaults(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User) and user.institution is not None
        components = seed_default_salary_components(user.institution)
        serializer = self.get_serializer(list(components.values()), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List salary structures", tags=["Payroll - Setup"]),
    retrieve=extend_schema(summary="Retrieve salary structure", tags=["Payroll - Setup"]),
    create=extend_schema(summary="Create salary structure", tags=["Payroll - Setup"]),
    update=extend_schema(summary="Update salary structure", tags=["Payroll - Setup"]),
    partial_update=extend_schema(
        summary="Partial update salary structure", tags=["Payroll - Setup"]
    ),
    destroy=extend_schema(summary="Soft-delete salary structure", tags=["Payroll - Setup"]),
)
class SalaryStructureViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for reusable salary structure templates."""

    queryset = (
        SalaryStructure.objects.filter(is_deleted=False)
        .prefetch_related("lines__component")
        .order_by("name")
    )
    serializer_class = SalaryStructureSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active"]
    search_fields = ["code", "name", "name_bn"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPayroll()]
        return [IsAuthenticated(), CanManagePayroll()]

    def perform_destroy(self, instance: SalaryStructure) -> None:
        instance.delete()

    @extend_schema(
        summary="Seed default Bangladeshi school salary structures",
        tags=["Payroll - Setup"],
        request=None,
        responses={200: SalaryStructureSerializer(many=True)},
    )
    @action(detail=False, methods=["post"])
    def seed_defaults(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User) and user.institution is not None
        structures = seed_default_salary_structures(user.institution)
        serializer = self.get_serializer(structures, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List salary structure lines", tags=["Payroll - Setup"]),
    retrieve=extend_schema(summary="Retrieve salary structure line", tags=["Payroll - Setup"]),
    create=extend_schema(summary="Create salary structure line", tags=["Payroll - Setup"]),
    update=extend_schema(summary="Update salary structure line", tags=["Payroll - Setup"]),
    partial_update=extend_schema(
        summary="Partial update salary structure line", tags=["Payroll - Setup"]
    ),
    destroy=extend_schema(summary="Delete salary structure line", tags=["Payroll - Setup"]),
)
class SalaryStructureLineViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for component formula lines attached to a SalaryStructure."""

    queryset = SalaryStructureLine.objects.select_related("structure", "component").all()
    serializer_class = SalaryStructureLineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["structure", "component"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPayroll()]
        return [IsAuthenticated(), CanManagePayroll()]


@extend_schema_view(
    list=extend_schema(summary="List staff salary profiles", tags=["Payroll - Profiles"]),
    retrieve=extend_schema(summary="Retrieve staff salary profile", tags=["Payroll - Profiles"]),
    create=extend_schema(summary="Create staff salary profile", tags=["Payroll - Profiles"]),
    update=extend_schema(summary="Update staff salary profile", tags=["Payroll - Profiles"]),
    partial_update=extend_schema(
        summary="Partial update staff salary profile", tags=["Payroll - Profiles"]
    ),
    destroy=extend_schema(summary="Soft-delete staff salary profile", tags=["Payroll - Profiles"]),
)
class StaffSalaryProfileViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for employee salary profiles, MPO split, PF, and banking details."""

    queryset = (
        StaffSalaryProfile.objects.filter(is_deleted=False)
        .select_related("staff", "structure")
        .prefetch_related("overrides__component")
        .order_by("staff__employee_id")
    )
    serializer_class = StaffSalaryProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "payment_method", "pf_enrolled", "structure"]
    search_fields = ["staff__employee_id", "staff__full_name_en", "staff__full_name_bn"]
    ordering_fields = ["basic_salary", "effective_from", "created_at"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPayroll()]
        return [IsAuthenticated(), CanManagePayroll()]

    def perform_destroy(self, instance: StaffSalaryProfile) -> None:
        instance.delete()

    @extend_schema(
        summary="Synchronize staff roster to salary profiles",
        description="Creates baseline salary profiles for active school staff members who do not yet have one.",
        responses={200: OpenApiTypes.OBJECT},
        tags=["Payroll - Profiles"],
    )
    @action(detail=False, methods=["post"], url_path="sync-roster")
    def sync_roster(self, request: Request) -> Response:
        """Create baseline salary profiles for active staff who don't have one yet."""
        institution = get_request_institution(request)
        active_staff = Staff.objects.filter(
            institution=institution,
            is_deleted=False,
            status=StaffStatus.ACTIVE,
        )
        existing_staff_ids = set(
            StaffSalaryProfile.objects.filter(
                institution=institution,
                is_deleted=False,
            ).values_list("staff_id", flat=True)
        )
        created_count = 0
        for staff_member in active_staff:
            if staff_member.id not in existing_staff_ids:
                StaffSalaryProfile.objects.create(
                    institution=institution,
                    staff=staff_member,
                    basic_salary=Decimal("0.00"),
                    payment_method="bank_transfer",
                    effective_from=timezone.localdate(),
                    is_active=True,
                )
                created_count += 1

        return Response(
            {
                "created": created_count,
                "total_staff": active_staff.count(),
                "message": f"Successfully synchronized {created_count} staff salary profile(s).",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(summary="List staff salary overrides", tags=["Payroll - Profiles"]),
    retrieve=extend_schema(summary="Retrieve staff salary override", tags=["Payroll - Profiles"]),
    create=extend_schema(summary="Create staff salary override", tags=["Payroll - Profiles"]),
    update=extend_schema(summary="Update staff salary override", tags=["Payroll - Profiles"]),
    partial_update=extend_schema(
        summary="Partial update staff salary override", tags=["Payroll - Profiles"]
    ),
    destroy=extend_schema(summary="Delete staff salary override", tags=["Payroll - Profiles"]),
)
class StaffSalaryOverrideViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for per-employee component overrides."""

    queryset = StaffSalaryOverride.objects.select_related("profile__staff", "component").all()
    serializer_class = StaffSalaryOverrideSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["profile", "component"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPayroll()]
        return [IsAuthenticated(), CanManagePayroll()]


@extend_schema_view(
    list=extend_schema(summary="List staff loans and advances", tags=["Payroll - Loans"]),
    retrieve=extend_schema(summary="Retrieve staff loan", tags=["Payroll - Loans"]),
    create=extend_schema(summary="Issue staff loan / advance", tags=["Payroll - Loans"]),
    update=extend_schema(summary="Update staff loan", tags=["Payroll - Loans"]),
    partial_update=extend_schema(summary="Partial update staff loan", tags=["Payroll - Loans"]),
    destroy=extend_schema(summary="Soft-delete staff loan", tags=["Payroll - Loans"]),
)
class StaffLoanViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for salary advances and loans recovered via monthly payroll."""

    queryset = (
        StaffLoan.objects.filter(is_deleted=False)
        .select_related("staff", "approved_by")
        .order_by("-disbursed_date", "-created_at")
    )
    serializer_class = StaffLoanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["staff", "loan_type", "status"]
    search_fields = ["staff__employee_id", "staff__full_name_en", "reason"]
    ordering_fields = ["disbursed_date", "remaining_balance", "created_at"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), CanViewPayroll()]
        return [IsAuthenticated(), CanManagePayroll()]

    def perform_destroy(self, instance: StaffLoan) -> None:
        instance.delete()


@extend_schema_view(
    list=extend_schema(summary="List monthly payroll runs", tags=["Payroll - Runs"]),
    retrieve=extend_schema(summary="Retrieve monthly payroll run", tags=["Payroll - Runs"]),
)
class PayrollRunViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """View and process monthly payroll batches, bonuses, GL posting, and BEFTN exports."""

    queryset = (
        PayrollRun.objects.filter(is_deleted=False)
        .select_related("journal_entry", "prepared_by", "reviewed_by", "approved_by")
        .prefetch_related("payslips")
        .order_by("-year", "-month")
    )
    serializer_class = PayrollRunSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["year", "month", "status", "is_locked"]
    ordering_fields = ["year", "month", "total_net_pay", "created_at"]

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ("list", "retrieve", "bank_advice"):
            return [IsAuthenticated(), CanViewPayroll()]
        if self.action in ("generate", "apply_bonus", "review"):
            return [IsAuthenticated(), CanManagePayroll()]
        return [IsAuthenticated(), CanApprovePayroll()]

    @extend_schema(
        summary="Generate or recalculate a draft monthly payroll run",
        tags=["Payroll - Runs"],
        request=GeneratePayrollRunSerializer,
        responses={200: PayrollRunSerializer},
    )
    @action(detail=False, methods=["post"])
    def generate(self, request: Request) -> Response:
        serializer = GeneratePayrollRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        assert isinstance(user, User) and user.institution is not None
        data = serializer.validated_data
        try:
            run = generate_payroll_run(
                institution=user.institution,
                year=data["year"],
                month=data["month"],
                user=user,
                working_days_in_month=data.get("working_days_in_month"),
                absence_deduction_basis=data["absence_deduction_basis"],
                title=data.get("title", ""),
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Apply batch Eid/Festival bonus to a DRAFT payroll run",
        tags=["Payroll - Runs"],
        request=ApplyBonusSerializer,
        responses={200: PayrollRunSerializer},
    )
    @action(detail=True, methods=["post"])
    def apply_bonus(self, request: Request, pk: Any = None) -> Response:
        payroll_run = self.get_object()
        serializer = ApplyBonusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            run = apply_bonus_to_run(
                payroll_run=payroll_run,
                bonus_title=data["bonus_title"],
                percentage_of_basic=data.get("percentage_of_basic"),
                fixed_amount=data.get("fixed_amount"),
                staff_type=data.get("staff_type") or None,
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Mark a DRAFT payroll run as REVIEWED",
        tags=["Payroll - Runs"],
        request=None,
        responses={200: PayrollRunSerializer},
    )
    @action(detail=True, methods=["post"])
    def review(self, request: Request, pk: Any = None) -> Response:
        payroll_run = self.get_object()
        user = request.user
        assert isinstance(user, User)
        try:
            run = review_payroll_run(payroll_run, user)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Approve a payroll run for disbursement",
        tags=["Payroll - Runs"],
        request=None,
        responses={200: PayrollRunSerializer},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: Any = None) -> Response:
        payroll_run = self.get_object()
        user = request.user
        assert isinstance(user, User)
        try:
            run = approve_payroll_run(payroll_run, user)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Mark an approved payroll run as PAID and settle loan installments",
        tags=["Payroll - Runs"],
        request=MarkPaidSerializer,
        responses={200: PayrollRunSerializer},
    )
    @action(detail=True, methods=["post"])
    def mark_paid(self, request: Request, pk: Any = None) -> Response:
        payroll_run = self.get_object()
        serializer = MarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        assert isinstance(user, User)
        try:
            run = mark_payroll_run_paid(
                payroll_run=payroll_run,
                user=user,
                payment_reference=serializer.validated_data.get("payment_reference", ""),
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Permanently lock a PAID payroll run",
        tags=["Payroll - Runs"],
        request=None,
        responses={200: PayrollRunSerializer},
    )
    @action(detail=True, methods=["post"])
    def lock(self, request: Request, pk: Any = None) -> Response:
        payroll_run = self.get_object()
        user = request.user
        assert isinstance(user, User)
        try:
            run = lock_payroll_run(payroll_run, user)
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Post payroll run to General Ledger (apps.accounting)",
        tags=["Payroll - Runs"],
        request=PostAccountingSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["post"])
    def post_to_accounting(self, request: Request, pk: Any = None) -> Response:
        payroll_run = self.get_object()
        serializer = PostAccountingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        assert isinstance(user, User)
        data = serializer.validated_data
        try:
            entry = post_payroll_to_accounting(
                payroll_run=payroll_run,
                user=user,
                posting_date=data.get("posting_date"),
                bank_account_code=data["bank_account_code"],
                cash_account_code=data["cash_account_code"],
                salary_expense_code=data["salary_expense_code"],
                liability_account_code=data["liability_account_code"],
            )
        except DjangoValidationError as exc:
            _raise_drf_validation(exc)
        return Response(
            {
                "journal_entry_id": str(entry.id),
                "voucher_no": entry.voucher_no,
                "total_debit": str(entry.total_debit),
                "total_credit": str(entry.total_credit),
                "status": entry.status,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Export BEFTN / Bank Advice sheet in XLSX or CSV format",
        tags=["Payroll - Runs"],
        parameters=[
            OpenApiParameter(
                name="export_format",
                type=OpenApiTypes.STR,
                enum=["xlsx", "csv"],
                default="xlsx",
            ),
            OpenApiParameter(
                name="payment_method",
                type=OpenApiTypes.STR,
                required=False,
            ),
        ],
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=["get"])
    def bank_advice(self, request: Request, pk: Any = None) -> HttpResponse:
        payroll_run = self.get_object()
        fmt = request.query_params.get("export_format", "xlsx").lower()
        payment_method = request.query_params.get("payment_method") or None
        base_name = f"bank-advice-{payroll_run.year}-{payroll_run.month:02d}"

        if fmt == "csv":
            payload = export_bank_advice_csv(payroll_run, payment_method=payment_method)
            response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="{base_name}.csv"'
            return response

        payload = export_bank_advice_xlsx(payroll_run, payment_method=payment_method)
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{base_name}.xlsx"'
        return response


@extend_schema_view(
    list=extend_schema(summary="List payslips", tags=["Payroll - Payslips"]),
    retrieve=extend_schema(summary="Retrieve payslip details", tags=["Payroll - Payslips"]),
)
class PayslipViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only payslips with self-service endpoint and bilingual PDF download."""

    queryset = (
        Payslip.objects.select_related(
            "payroll_run", "staff", "staff__department", "staff__designation"
        )
        .prefetch_related("lines")
        .order_by("-payroll_run__year", "-payroll_run__month", "staff__employee_id")
    )
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated, IsPayrollAdminOrSelf]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["payroll_run", "staff", "is_paid", "payment_method"]
    search_fields = ["staff__employee_id", "staff__full_name_en", "staff__full_name_bn"]
    ordering_fields = ["net_payable", "gross_earnings", "created_at"]

    def get_queryset(self) -> Any:
        qs = super().get_queryset()
        if CanViewPayroll().has_permission(self.request, self):
            return qs
        return qs.filter(staff__user=self.request.user)

    @extend_schema(
        summary="List authenticated employee's own payslips",
        tags=["Payroll - Payslips"],
        responses={200: PayslipSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def my_payslips(self, request: Request) -> Response:
        qs = super().get_queryset().filter(staff__user=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Download bilingual Payslip PDF",
        tags=["Payroll - Payslips"],
        responses={(200, "application/pdf"): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=["get"])
    def pdf(self, request: Request, pk: Any = None) -> HttpResponse:
        payslip = self.get_object()
        pdf_bytes = render_payslip_pdf(payslip)
        filename = (
            f"payslip-{payslip.staff.employee_id}-"
            f"{payslip.payroll_run.year}-{payslip.payroll_run.month:02d}.pdf"
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
