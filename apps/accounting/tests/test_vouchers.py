"""Tests for journal entries, voucher posting, voiding, and fee integration."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounting.models import (
    Account,
    FiscalYear,
    VoucherStatus,
    VoucherType,
)
from apps.accounting.services.account_service import seed_default_chart_of_accounts
from apps.accounting.services.payment_integration_service import (
    create_voucher_for_fee_payment,
)
from apps.accounting.services.voucher_service import (
    create_journal_entry,
    get_next_voucher_number,
    post_journal_entry,
    void_journal_entry,
)
from apps.accounts.models import User
from apps.fees.models import FeeHead, Invoice, Payment, PaymentMethod, PaymentStatus, RecurrenceType
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model Academy",
        name_bn="ঢাকা মডেল একাডেমি",
        eiin="123456",
    )


@pytest.fixture
def accountant_user(db, institution) -> User:
    return User.objects.create_user(
        username="accountant_user",
        password="ValidPassword123!",
        institution=institution,
        phone="+8801711000001",
    )


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
class TestVoucherService:
    """Test voucher sequencing, double-entry validation, posting, and voiding."""

    def test_gap_free_sequential_voucher_numbers(self, institution, fiscal_year):
        v1 = get_next_voucher_number(institution, fiscal_year, VoucherType.PAYMENT)
        assert v1 == "PV-2026-000001"
        v2 = get_next_voucher_number(institution, fiscal_year, VoucherType.PAYMENT)
        assert v2 == "PV-2026-000002"
        v_rv = get_next_voucher_number(institution, fiscal_year, VoucherType.RECEIPT)
        assert v_rv == "RV-2026-000001"

    def test_create_journal_entry_balanced(self, institution, fiscal_year, coa, accountant_user):
        cash = coa["1010"]  # Cash in Hand (Asset)
        salaries = coa["5010"]  # Teachers Salaries (Expense)

        entry = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.PAYMENT,
            date=date(2026, 8, 10),
            narration="Teacher salary payment for July",
            items=[
                {"account": salaries, "debit": Decimal("50000.00"), "credit": Decimal("0.00")},
                {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("50000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )

        assert entry.voucher_no.startswith("PV-")
        assert entry.status == VoucherStatus.DRAFT
        assert entry.total_debit == Decimal("50000.00")
        assert entry.total_credit == Decimal("50000.00")
        assert entry.items.count() == 2

    def test_create_journal_entry_unbalanced_fails(self, institution, fiscal_year, coa):
        cash = coa["1010"]
        salaries = coa["5010"]

        with pytest.raises(ValidationError, match="Total debits .* must equal total credits"):
            create_journal_entry(
                institution=institution,
                voucher_type=VoucherType.PAYMENT,
                date=date(2026, 8, 10),
                narration="Unbalanced test",
                items=[
                    {"account": salaries, "debit": Decimal("50000.00"), "credit": Decimal("0.00")},
                    {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("45000.00")},
                ],
                fiscal_year=fiscal_year,
            )

    def test_post_journal_entry_updates_account_balances(
        self, institution, fiscal_year, coa, accountant_user
    ):
        cash = coa["1010"]
        salaries = coa["5010"]

        assert cash.current_balance == Decimal("0.00")
        assert salaries.current_balance == Decimal("0.00")

        entry = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.PAYMENT,
            date=date(2026, 8, 10),
            narration="Salary payment",
            items=[
                {"account": salaries, "debit": Decimal("30000.00"), "credit": Decimal("0.00")},
                {"account": cash, "debit": Decimal("0.00"), "credit": Decimal("30000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )

        posted_entry = post_journal_entry(entry, user=accountant_user)
        assert posted_entry.status == VoucherStatus.POSTED
        assert posted_entry.posted_by == accountant_user
        assert posted_entry.posted_at is not None

        # Reload accounts from DB
        cash.refresh_from_db()
        salaries.refresh_from_db()

        # Asset (Cash) credited -> balance decreases (-30000)
        assert cash.current_balance == Decimal("-30000.00")
        # Expense (Salary) debited -> balance increases (+30000)
        assert salaries.current_balance == Decimal("30000.00")

    def test_void_journal_entry_reverses_balances(
        self, institution, fiscal_year, coa, accountant_user
    ):
        cash = coa["1010"]
        tuition = coa["4010"]  # Tuition fee (Income)

        # Receipt voucher: Debit Cash, Credit Tuition
        entry = create_journal_entry(
            institution=institution,
            voucher_type=VoucherType.RECEIPT,
            date=date(2026, 8, 15),
            narration="Tuition fee collection",
            items=[
                {"account": cash, "debit": Decimal("10000.00"), "credit": Decimal("0.00")},
                {"account": tuition, "debit": Decimal("0.00"), "credit": Decimal("10000.00")},
            ],
            fiscal_year=fiscal_year,
            created_by=accountant_user,
        )

        post_journal_entry(entry, user=accountant_user)
        cash.refresh_from_db()
        tuition.refresh_from_db()
        assert cash.current_balance == Decimal("10000.00")
        assert tuition.current_balance == Decimal("10000.00")

        # Void entry
        voided_entry = void_journal_entry(
            entry, user=accountant_user, reason="Bounced cheque / mistake"
        )
        assert voided_entry.status == VoucherStatus.VOID
        assert voided_entry.void_reason == "Bounced cheque / mistake"

        cash.refresh_from_db()
        tuition.refresh_from_db()
        assert cash.current_balance == Decimal("0.00")
        assert tuition.current_balance == Decimal("0.00")

    def test_fee_payment_automatic_voucher_integration(
        self, institution, fiscal_year, coa, accountant_user
    ):
        """Task 15 Payment -> Task 17 Receipt Voucher integration."""
        session = AcademicSession.objects.create(
            institution=institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        student = Student.objects.create(
            institution=institution,
            student_id="STU202601",
            name_en="Sifat Rahman",
            dob=date(2010, 5, 5),
            gender="male",
            admission_date=date(2026, 1, 1),
        )
        invoice = Invoice.objects.create(
            institution=institution,
            student=student,
            session=session,
            invoice_number="INV-2026-0001",
            title="July Tuition Fee",
            subtotal_amount=Decimal("2500.00"),
            total_payable=Decimal("2500.00"),
            due_amount=Decimal("2500.00"),
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 7, 25),
        )
        FeeHead.objects.create(
            institution=institution,
            name_en="Monthly Tuition Fee",
            code="TUITION",
            account_code="4010",
            recurrence=RecurrenceType.MONTHLY,
        )

        payment = Payment.objects.create(
            institution=institution,
            invoice=invoice,
            student=student,
            amount=Decimal("2500.00"),
            payment_method=PaymentMethod.CASH,
            status=PaymentStatus.SUCCESSFUL,
            idempotency_key="pay_test_001",
            payment_date=timezone.now(),
            received_by=accountant_user,
        )

        # Call integration service
        voucher = create_voucher_for_fee_payment(payment, user=accountant_user)
        assert voucher.voucher_type == VoucherType.RECEIPT
        assert voucher.status == VoucherStatus.POSTED
        assert voucher.total_debit == Decimal("2500.00")
        assert voucher.total_credit == Decimal("2500.00")

        # Cash in hand credited +2500 and Tuition fee credited +2500
        cash = coa["1010"]
        tuition = coa["4010"]
        cash.refresh_from_db()
        tuition.refresh_from_db()
        assert cash.current_balance == Decimal("2500.00")
        assert tuition.current_balance == Decimal("2500.00")
