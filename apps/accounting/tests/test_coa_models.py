"""Tests for Chart of Accounts (COA) models and services."""

from datetime import date

import pytest
from django.db import IntegrityError

from apps.accounting.models import Account, AccountType, FiscalYear
from apps.accounting.services.account_service import (
    seed_default_chart_of_accounts,
)
from apps.institutions.models import Institution


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Ideal College",
        name_bn="ঢাকা আইডিয়াল কলেজ",
        eiin="123456",
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


@pytest.mark.django_db
class TestChartOfAccounts:
    """Test COA structure, seeding, constraints, and balance computation."""

    def test_seed_default_chart_of_accounts(self, institution):
        """Verify seeding creates top groups and standard sub-accounts."""
        created = seed_default_chart_of_accounts(institution)
        assert len(created) > 20

        # Check top-level group accounts exist
        top_groups = Account.objects.filter(institution=institution, parent__isnull=True)
        assert top_groups.count() == 5
        type_codes = {g.account_code: g.account_type for g in top_groups}
        assert type_codes["1000"] == AccountType.ASSET
        assert type_codes["2000"] == AccountType.LIABILITY
        assert type_codes["3000"] == AccountType.EQUITY
        assert type_codes["4000"] == AccountType.INCOME
        assert type_codes["5000"] == AccountType.EXPENSE

        # Check leaf operational accounts
        cash_in_hand = Account.objects.get(institution=institution, account_code="1010")
        assert not cash_in_hand.is_group
        assert cash_in_hand.normal_balance == "debit"

        tuition_fee = Account.objects.get(institution=institution, account_code="4010")
        assert tuition_fee.account_type == AccountType.INCOME
        assert tuition_fee.normal_balance == "credit"

        # Check idempotent second run does not duplicate accounts
        seed_default_chart_of_accounts(institution)
        assert Account.objects.filter(institution=institution, account_code="1010").count() == 1

    def test_unique_account_code_per_institution(self, institution):
        """Cannot create duplicate active account code within same institution."""
        Account.objects.create(
            institution=institution,
            account_code="9999",
            name_en="Misc Account",
            account_type=AccountType.ASSET,
        )
        with pytest.raises(IntegrityError):
            Account.objects.create(
                institution=institution,
                account_code="9999",
                name_en="Duplicate Misc",
                account_type=AccountType.EXPENSE,
            )

    def test_cross_tenant_account_code_isolation(self, institution):
        """Different institutions may use the same account codes."""
        other_inst = Institution.objects.create(name_en="Chittagong High School")
        a1 = Account.objects.create(
            institution=institution,
            account_code="1010",
            name_en="Cash in Hand",
            account_type=AccountType.ASSET,
        )
        a2 = Account.objects.create(
            institution=other_inst,
            account_code="1010",
            name_en="Cash in Hand",
            account_type=AccountType.ASSET,
        )
        assert a1.account_code == a2.account_code
        assert a1.institution_id != a2.institution_id

    def test_normal_balance_rules(self, institution):
        """Assets & Expenses are debit normal; Liabilities, Equity & Income are credit normal."""
        asset = Account.objects.create(
            institution=institution,
            account_code="1001",
            name_en="Cash",
            account_type=AccountType.ASSET,
        )
        expense = Account.objects.create(
            institution=institution,
            account_code="5001",
            name_en="Rent",
            account_type=AccountType.EXPENSE,
        )
        liability = Account.objects.create(
            institution=institution,
            account_code="2001",
            name_en="Loan",
            account_type=AccountType.LIABILITY,
        )
        equity = Account.objects.create(
            institution=institution,
            account_code="3001",
            name_en="Capital",
            account_type=AccountType.EQUITY,
        )
        income = Account.objects.create(
            institution=institution,
            account_code="4001",
            name_en="Fees",
            account_type=AccountType.INCOME,
        )

        assert asset.normal_balance == "debit"
        assert expense.normal_balance == "debit"
        assert liability.normal_balance == "credit"
        assert equity.normal_balance == "credit"
        assert income.normal_balance == "credit"
