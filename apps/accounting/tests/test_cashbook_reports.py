"""Tests for Cashbook, Financial Reports, PDF Generation, and REST APIs."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounting.models import (
    Account,
    FiscalYear,
    VoucherType,
)
from apps.accounting.services.account_service import seed_default_chart_of_accounts
from apps.accounting.services.financial_reports_service import (
    get_balance_sheet,
    get_daily_cashbook,
    get_income_statement,
    get_trial_balance,
)
from apps.accounting.services.voucher_pdf_service import generate_voucher_pdf
from apps.accounting.services.voucher_service import (
    create_journal_entry,
    post_journal_entry,
)
from apps.accounts.models import User
from apps.institutions.models import Institution


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Chittagong Model School",
        name_bn="চট্টগ্রাম মডেল স্কুল",
        eiin="654321",
    )


@pytest.fixture
def accountant_user(db, institution) -> User:
    user = User.objects.create_user(
        username="acct_admin",
        password="ValidPassword123!",
        institution=institution,
        phone="+8801811000002",
        user_type="admin",
        is_staff=True,
    )
    return user


@pytest.fixture
def api_client(accountant_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=accountant_user)
    return client


@pytest.fixture
def fiscal_year(institution) -> FiscalYear:
    return FiscalYear.objects.create(
        institution=institution,
        name="FY 2026-2027",
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        is_current=True,
    )


@pytest.fixture
def coa(institution):
    seed_default_chart_of_accounts(institution)
    return {a.account_code: a for a in Account.objects.filter(institution=institution)}


@pytest.mark.django_db
class TestCashbookAndReports:
    """Test daily cashbook, financial statements, PDF voucher and REST endpoints."""

    def test_daily_cashbook_and_dayend_closing(
        self, institution, fiscal_year, coa, accountant_user, api_client
    ):
        cash = coa["1010"]  # Cash in Hand
        tuition = coa["4010"]  # Tuition fee (Income)
        utility = coa["5040"]  # Electricity / Utility (Expense)

        # 1. Post a Receipt Voucher on 2026-08-01: +15000 Cash
        rv = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.RECEIPT,
            date=date(2026, 8, 1),
            narration="Cash fee collected",
            items=[
                {"account": cash, "debit": Decimal("15000.00"), "credit": Decimal("0.00")},
                {"account": tuition, "debit": Decimal("0.00"), "credit": Decimal("15000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(rv, user=accountant_user)

        # 2. Post a Payment Voucher on 2026-08-01: -3000 Cash
        pv = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.PAYMENT,
            date=date(2026, 8, 1),
            narration="Electricity bill cash payment",
            items=[
                {"account": utility, "debit": Decimal("3000.00"), "credit": Decimal("0.00")},
                {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("3000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(pv, user=accountant_user)

        # Test Cashbook Service
        book = get_daily_cashbook(institution, report_date=date(2026, 8, 1), cash_account=cash)
        assert Decimal(str(book["opening_balance"])) == Decimal("0.00")
        assert Decimal(str(book["total_receipts"])) == Decimal("15000.00")
        assert Decimal(str(book["total_payments"])) == Decimal("3000.00")
        assert Decimal(str(book["closing_balance"])) == Decimal("12000.00")
        assert len(book["transactions"]) == 2

        # Test Cashbook API GET
        url = "/api/v1/accounting/cashbook/"
        res_get = api_client.get(url, {"date": "2026-08-01", "account_id": str(cash.id)})
        assert res_get.status_code == status.HTTP_200_OK
        assert Decimal(str(res_get.data["closing_balance"])) == Decimal("12000.00")

        # Test Cashbook Day-End Closing API POST
        close_payload = {
            "account": str(cash.id),
            "date": "2026-08-01",
            "physical_count": "12000.00",
            "note": "Reconciled with cashier drawer perfectly",
        }
        res_post = api_client.post(url, close_payload, format="json")
        assert res_post.status_code == status.HTTP_201_CREATED
        assert Decimal(str(res_post.data["discrepancy"])) == Decimal("0.00")

    def test_trial_balance_balances_perfectly(self, institution, fiscal_year, coa, accountant_user):
        cash = coa["1010"]
        tuition = coa["4010"]
        salaries = coa["5010"]

        # Transaction 1: Fee 20,000
        e1 = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.RECEIPT,
            date=date(2026, 8, 5),
            narration="Fee",
            items=[
                {"account": cash, "debit": Decimal("20000.00"), "credit": Decimal("0.00")},
                {"account": tuition, "debit": Decimal("0.00"), "credit": Decimal("20000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(e1, user=accountant_user)

        # Transaction 2: Salary 12,000
        e2 = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.PAYMENT,
            date=date(2026, 8, 6),
            narration="Salary",
            items=[
                {"account": salaries, "debit": Decimal("12000.00"), "credit": Decimal("0.00")},
                {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("12000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(e2, user=accountant_user)

        tb = get_trial_balance(institution, as_of_date=date(2026, 8, 10))
        assert tb["is_balanced"] is True
        assert Decimal(str(tb["total_debits"])) == Decimal("20000.00")
        assert Decimal(str(tb["total_credits"])) == Decimal("20000.00")

    def test_income_statement_and_balance_sheet(
        self, institution, fiscal_year, coa, accountant_user, api_client
    ):
        cash = coa["1010"]
        tuition = coa["4010"]
        salaries = coa["5010"]

        # Revenue: 50,000
        e1 = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.RECEIPT,
            date=date(2026, 8, 5),
            narration="Tuition",
            items=[
                {"account": cash, "debit": Decimal("50000.00"), "credit": Decimal("0.00")},
                {"account": tuition, "debit": Decimal("0.00"), "credit": Decimal("50000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(e1, user=accountant_user)

        # Expense: 35,000
        e2 = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.PAYMENT,
            date=date(2026, 8, 6),
            narration="Salaries",
            items=[
                {"account": salaries, "debit": Decimal("35000.00"), "credit": Decimal("0.00")},
                {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("35000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(e2, user=accountant_user)

        # Test Income Statement
        pnl = get_income_statement(
            institution, start_date=date(2026, 8, 1), end_date=date(2026, 8, 31)
        )
        assert Decimal(str(pnl["total_income"])) == Decimal("50000.00")
        assert Decimal(str(pnl["total_expense"])) == Decimal("35000.00")
        assert Decimal(str(pnl["net_surplus"])) == Decimal("15000.00")

        # Test Balance Sheet
        bs = get_balance_sheet(institution, as_of_date=date(2026, 8, 31))
        # Total Assets = 15,000 (Cash balance)
        assert Decimal(str(bs["total_assets"])) == Decimal("15000.00")
        # Total Liabilities & Equity = Retained surplus (15,000)
        assert Decimal(str(bs["total_liabilities_and_equity"])) == Decimal("15000.00")
        assert bs["is_balanced"] is True

        # Test Reports API Endpoints
        res_tb = api_client.get("/api/v1/accounting/reports/trial_balance/")
        assert res_tb.status_code == status.HTTP_200_OK
        assert res_tb.data["is_balanced"] is True

        res_pnl = api_client.get("/api/v1/accounting/reports/income_statement/")
        assert res_pnl.status_code == status.HTTP_200_OK
        assert Decimal(str(res_pnl.data["net_surplus"])) == Decimal("15000.00")

        res_bs = api_client.get("/api/v1/accounting/reports/balance_sheet/")
        assert res_bs.status_code == status.HTTP_200_OK
        assert res_bs.data["is_balanced"] is True

    def test_voucher_pdf_generation(
        self, institution, fiscal_year, coa, accountant_user, api_client
    ):
        cash = coa["1010"]
        tuition = coa["4010"]

        entry = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.RECEIPT,
            date=date(2026, 8, 12),
            narration="Monthly tuition collection - August 2026",
            items=[
                {
                    "account": cash,
                    "debit": Decimal("12500.00"),
                    "credit": Decimal("0.00"),
                    "narration": "Cash received",
                },
                {
                    "account": tuition,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("12500.00"),
                    "narration": "August tuition",
                },
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )
        post_journal_entry(entry, user=accountant_user)

        pdf_bytes = generate_voucher_pdf(entry)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF")

        # Test PDF API endpoint
        url = f"/api/v1/accounting/vouchers/{entry.id}/pdf/"
        res_pdf = api_client.get(url)
        assert res_pdf.status_code == status.HTTP_200_OK
        assert res_pdf["Content-Type"] == "application/pdf"
        assert len(res_pdf.content) > 1000
