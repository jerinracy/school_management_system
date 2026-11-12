"""REST API views for accounting, vouchers, cashbook, and financial statements."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.models import (
    Account,
    CashbookClosing,
    FiscalYear,
    JournalEntry,
)
from apps.accounting.permissions import (
    IsAccountantOrAdmin,
)
from apps.accounting.serializers import (
    AccountSerializer,
    CashbookClosingSerializer,
    DailyCashbookQuerySerializer,
    FiscalYearSerializer,
    JournalEntrySerializer,
)
from apps.accounting.services.account_service import (
    recalculate_account_balances,
    seed_default_chart_of_accounts,
)
from apps.accounting.services.financial_reports_service import (
    get_balance_sheet,
    get_daily_cashbook,
    get_income_statement,
    get_trial_balance,
)
from apps.accounting.services.voucher_pdf_service import generate_voucher_pdf
from apps.accounting.services.voucher_service import (
    post_journal_entry,
    void_journal_entry,
)
from apps.core.mixins import TenantScopedMixin


@extend_schema_view(
    list=extend_schema(summary="List fiscal years", tags=["Accounting - Fiscal Years"]),
    retrieve=extend_schema(summary="Retrieve fiscal year", tags=["Accounting - Fiscal Years"]),
    create=extend_schema(summary="Create fiscal year", tags=["Accounting - Fiscal Years"]),
    update=extend_schema(summary="Update fiscal year", tags=["Accounting - Fiscal Years"]),
    destroy=extend_schema(summary="Delete fiscal year", tags=["Accounting - Fiscal Years"]),
)
class FiscalYearViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """ViewSet for managing financial fiscal years."""

    queryset = FiscalYear.objects.all().order_by("-start_date")
    serializer_class = FiscalYearSerializer
    permission_classes = [IsAuthenticated, IsAccountantOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_current", "is_closed"]
    search_fields = ["name"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    @extend_schema(summary="Set fiscal year as current active", tags=["Accounting - Fiscal Years"])
    @action(detail=True, methods=["post"])
    def set_current(self, request: Request, pk: Any = None) -> Response:
        fy = self.get_object()
        FiscalYear.objects.filter(institution=fy.institution).update(is_current=False)
        fy.is_current = True
        fy.save(update_fields=["is_current", "updated_at"])
        return Response({"detail": f"Fiscal year '{fy.name}' is now active."})

    @extend_schema(summary="Close fiscal year", tags=["Accounting - Fiscal Years"])
    @action(detail=True, methods=["post"])
    def close(self, request: Request, pk: Any = None) -> Response:
        fy = self.get_object()
        fy.is_closed = True
        fy.save(update_fields=["is_closed", "updated_at"])
        return Response({"detail": f"Fiscal year '{fy.name}' has been closed."})


@extend_schema_view(
    list=extend_schema(summary="List accounts (COA)", tags=["Accounting - Chart of Accounts"]),
    retrieve=extend_schema(summary="Retrieve account", tags=["Accounting - Chart of Accounts"]),
    create=extend_schema(summary="Create account", tags=["Accounting - Chart of Accounts"]),
    update=extend_schema(summary="Update account", tags=["Accounting - Chart of Accounts"]),
    destroy=extend_schema(summary="Delete account", tags=["Accounting - Chart of Accounts"]),
)
class AccountViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """ViewSet for hierarchical Chart of Accounts."""

    queryset = Account.objects.select_related("parent").all().order_by("account_code")
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, IsAccountantOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["account_type", "subtype", "is_group", "is_system"]
    search_fields = ["account_code", "name_en", "name_bn"]
    ordering_fields = ["account_code", "name_en", "current_balance"]

    @extend_schema(
        summary="Seed standard Bangladeshi school COA", tags=["Accounting - Chart of Accounts"]
    )
    @action(detail=False, methods=["post"])
    def seed_default(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required to seed accounts.")
        seed_default_chart_of_accounts(institution)
        return Response(
            {"detail": "Default Bangladeshi school Chart of Accounts successfully seeded."}
        )

    @extend_schema(
        summary="Recalculate all account balances", tags=["Accounting - Chart of Accounts"]
    )
    @action(detail=False, methods=["post"])
    def recalculate(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required.")
        recalculate_account_balances(institution)
        return Response({"detail": "All account balances successfully recalculated."})

    @extend_schema(
        summary="Get hierarchical tree of accounts", tags=["Accounting - Chart of Accounts"]
    )
    @action(detail=False, methods=["get"])
    def tree(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            return Response([])

        accounts = Account.objects.filter(institution=institution).order_by("account_code")
        nodes_by_id: dict[UUID, dict[str, Any]] = {}
        roots: list[dict[str, Any]] = []

        for acct in accounts:
            nodes_by_id[acct.id] = {
                "id": str(acct.id),
                "account_code": acct.account_code,
                "name_en": acct.name_en,
                "name_bn": acct.name_bn,
                "account_type": acct.account_type,
                "subtype": acct.subtype,
                "is_group": acct.is_group,
                "is_system": acct.is_system,
                "current_balance": str(acct.current_balance),
                "children": [],
            }

        for acct in accounts:
            node = nodes_by_id[acct.id]
            if acct.parent_id and acct.parent_id in nodes_by_id:
                nodes_by_id[acct.parent_id]["children"].append(node)
            else:
                roots.append(node)

        return Response(roots)


@extend_schema_view(
    list=extend_schema(summary="List journal entries", tags=["Accounting - Journal Entries"]),
    retrieve=extend_schema(summary="Retrieve journal entry", tags=["Accounting - Journal Entries"]),
    create=extend_schema(summary="Create journal entry", tags=["Accounting - Journal Entries"]),
    update=extend_schema(summary="Update journal entry", tags=["Accounting - Journal Entries"]),
    destroy=extend_schema(summary="Delete journal entry", tags=["Accounting - Journal Entries"]),
)
class JournalEntryViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """ViewSet for Journal Entries / Accounting Vouchers."""

    queryset = (
        JournalEntry.objects.select_related("fiscal_year", "posted_by", "voided_by", "created_by")
        .prefetch_related("items__account")
        .all()
        .order_by("-date", "-created_at")
    )
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated, IsAccountantOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["voucher_type", "status", "fiscal_year", "date"]
    search_fields = ["voucher_no", "narration", "cheque_no", "payment_reference"]
    ordering_fields = ["date", "voucher_no", "total_debit", "created_at"]

    @extend_schema(
        summary="Post journal entry to general ledger", tags=["Accounting - Journal Entries"]
    )
    @action(detail=True, methods=["post"])
    def post(self, request: Request, pk: Any = None) -> Response:
        entry = self.get_object()
        user = request.user if request.user and request.user.is_authenticated else None
        posted_entry = post_journal_entry(entry, user=user)
        return Response(JournalEntrySerializer(posted_entry).data)

    @extend_schema(summary="Void journal entry", tags=["Accounting - Journal Entries"])
    @action(detail=True, methods=["post"])
    def void(self, request: Request, pk: Any = None) -> Response:
        entry = self.get_object()
        reason = request.data.get("reason", "")
        user = request.user if request.user and request.user.is_authenticated else None
        voided_entry = void_journal_entry(entry, user=user, reason=reason)
        return Response(JournalEntrySerializer(voided_entry).data)

    @extend_schema(summary="Download official voucher PDF", tags=["Accounting - Journal Entries"])
    @action(detail=True, methods=["get"])
    def pdf(self, request: Request, pk: Any = None) -> HttpResponse:
        entry = self.get_object()
        pdf_bytes = generate_voucher_pdf(entry)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = f"voucher_{entry.voucher_no}_{entry.date}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class CashbookView(APIView):
    """Daily cashbook report & cashier day-end reconciliation view."""

    permission_classes = [IsAuthenticated, IsAccountantOrAdmin]

    @extend_schema(
        summary="Get daily cashbook statement",
        parameters=[
            OpenApiParameter("date", str, description="Date in YYYY-MM-DD (defaults to today)"),
            OpenApiParameter("account_id", str, description="Cash or Bank Account UUID (optional)"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Accounting - Cashbook"],
    )
    def get(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required.")

        serializer = DailyCashbookQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        report_date = serializer.validated_data.get("date") or timezone.now().date()
        account_id = serializer.validated_data.get("account_id")

        cash_account = None
        if account_id:
            try:
                cash_account = Account.objects.get(id=account_id, institution=institution)
            except Account.DoesNotExist:
                raise ValidationError("Account not found.") from None

        result = get_daily_cashbook(institution, report_date=report_date, cash_account=cash_account)
        return Response(result)

    @extend_schema(
        summary="Close daily cashier cashbook",
        request=CashbookClosingSerializer,
        responses={201: CashbookClosingSerializer},
        tags=["Accounting - Cashbook"],
    )
    def post(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required.")

        account_id = request.data.get("account")
        closing_date_raw = request.data.get("date")
        closing_date = parse_date(closing_date_raw) if closing_date_raw else timezone.now().date()
        physical_count_val = request.data.get("physical_count", "0.00")
        note = request.data.get("note", "")

        try:
            account = Account.objects.get(id=str(account_id), institution=institution)
        except (Account.DoesNotExist, ValueError):
            raise ValidationError({"account": "Invalid cash account."}) from None

        physical_count = Decimal(str(physical_count_val))

        # Compute book numbers
        book_data = get_daily_cashbook(institution, report_date=closing_date, cash_account=account)
        closing_balance = Decimal(str(book_data["closing_balance"]))
        opening_balance = Decimal(str(book_data["opening_balance"]))
        total_receipts = Decimal(str(book_data["total_receipts"]))
        total_payments = Decimal(str(book_data["total_payments"]))
        discrepancy = physical_count - closing_balance

        closing_record, _ = CashbookClosing.objects.update_or_create(
            institution=institution,
            account=account,
            date=closing_date,
            defaults={
                "opening_balance": opening_balance,
                "total_receipts": total_receipts,
                "total_payments": total_payments,
                "closing_balance": closing_balance,
                "physical_count": physical_count,
                "discrepancy": discrepancy,
                "note": note,
                "closed_by": request.user,
            },
        )
        return Response(
            CashbookClosingSerializer(closing_record).data, status=status.HTTP_201_CREATED
        )


class FinancialReportsViewSet(viewsets.ViewSet):
    """Endpoints for Trial Balance, Income Statement, and Balance Sheet."""

    permission_classes = [IsAuthenticated, IsAccountantOrAdmin]

    @extend_schema(
        summary="Generate Trial Balance",
        parameters=[
            OpenApiParameter("as_of_date", str, description="As of date (YYYY-MM-DD)"),
            OpenApiParameter("fiscal_year_id", str, description="Fiscal year UUID (optional)"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Accounting - Financial Reports"],
    )
    @action(detail=False, methods=["get"])
    def trial_balance(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required.")

        as_of_date_raw = request.query_params.get("as_of_date")
        as_of_date = parse_date(as_of_date_raw) if as_of_date_raw else timezone.now().date()
        fy_id = request.query_params.get("fiscal_year_id")
        fy = FiscalYear.objects.filter(id=fy_id, institution=institution).first() if fy_id else None

        result = get_trial_balance(institution, as_of_date=as_of_date, fiscal_year=fy)
        return Response(result)

    @extend_schema(
        summary="Generate Income Statement (Profit & Loss / Surplus & Deficit)",
        parameters=[
            OpenApiParameter("start_date", str, description="Start date (YYYY-MM-DD)"),
            OpenApiParameter("end_date", str, description="End date (YYYY-MM-DD)"),
            OpenApiParameter("fiscal_year_id", str, description="Fiscal year UUID (optional)"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Accounting - Financial Reports"],
    )
    @action(detail=False, methods=["get"])
    def income_statement(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required.")

        start_date_raw = request.query_params.get("start_date")
        end_date_raw = request.query_params.get("end_date")
        start_date = parse_date(start_date_raw) if start_date_raw else None
        end_date = parse_date(end_date_raw) if end_date_raw else None
        fy_id = request.query_params.get("fiscal_year_id")
        fy = FiscalYear.objects.filter(id=fy_id, institution=institution).first() if fy_id else None

        result = get_income_statement(
            institution, start_date=start_date, end_date=end_date, fiscal_year=fy
        )
        return Response(result)

    @extend_schema(
        summary="Generate Balance Sheet",
        parameters=[
            OpenApiParameter("as_of_date", str, description="As of date (YYYY-MM-DD)"),
            OpenApiParameter("fiscal_year_id", str, description="Fiscal year UUID (optional)"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Accounting - Financial Reports"],
    )
    @action(detail=False, methods=["get"])
    def balance_sheet(self, request: Request) -> Response:
        institution = getattr(request.user, "institution", None)
        if not institution:
            raise ValidationError("Institution context required.")

        as_of_date_raw = request.query_params.get("as_of_date")
        as_of_date = parse_date(as_of_date_raw) if as_of_date_raw else timezone.now().date()
        fy_id = request.query_params.get("fiscal_year_id")
        fy = FiscalYear.objects.filter(id=fy_id, institution=institution).first() if fy_id else None

        result = get_balance_sheet(institution, as_of_date=as_of_date, fiscal_year=fy)
        return Response(result)
