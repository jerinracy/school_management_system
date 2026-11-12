"""Financial statements and Cashbook reporting service."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import Sum
from django.utils import timezone

from apps.accounting.models import (
    Account,
    AccountType,
    FiscalYear,
    JournalEntryItem,
    VoucherStatus,
)

if TYPE_CHECKING:
    from apps.institutions.models import Institution


def get_daily_cashbook(
    institution: "Institution",
    account: Account | None = None,
    report_date: date | None = None,
    cash_account: Account | None = None,
) -> dict[str, Any]:
    """Generate daily Cashbook statement for Cash in Hand or Bank accounts."""
    target_account = account or cash_account
    if target_account is None:
        target_account = (
            Account.objects.filter(institution=institution, account_code="1010").first()
            or Account.objects.filter(
                institution=institution, account_type=AccountType.ASSET, is_group=False
            ).first()
        )
    if not target_account:
        raise ValueError("No cash or bank account available for daily cashbook.")

    date_val = report_date or timezone.now().date()

    # Opening balance up to report_date - 1 day
    prior_debits = JournalEntryItem.objects.filter(
        institution=institution,
        account=target_account,
        entry__status=VoucherStatus.POSTED,
        entry__date__lt=date_val,
    ).aggregate(total=Sum("debit"))["total"] or Decimal("0.00")
    prior_credits = JournalEntryItem.objects.filter(
        institution=institution,
        account=target_account,
        entry__status=VoucherStatus.POSTED,
        entry__date__lt=date_val,
    ).aggregate(total=Sum("credit"))["total"] or Decimal("0.00")

    opening_balance = target_account.opening_balance + prior_debits - prior_credits

    # Day's transactions
    day_items = (
        JournalEntryItem.objects.filter(
            institution=institution,
            account=target_account,
            entry__status=VoucherStatus.POSTED,
            entry__date=date_val,
        )
        .select_related("entry")
        .order_by("entry__created_at")
    )

    transactions_list = []
    total_receipts = Decimal("0.00")
    total_payments = Decimal("0.00")

    for item in day_items:
        entry = item.entry
        transactions_list.append(
            {
                "voucher_no": entry.voucher_no,
                "voucher_type": entry.voucher_type,
                "narration": item.narration or entry.narration,
                "payee_or_payer": entry.payee_or_payer,
                "cheque_no": entry.cheque_no,
                "receipt_amount": item.debit,
                "payment_amount": item.credit,
            }
        )
        total_receipts += item.debit
        total_payments += item.credit

    closing_balance = opening_balance + total_receipts - total_payments

    return {
        "account_id": str(target_account.id),
        "account_code": target_account.account_code,
        "account_name": target_account.name_en,
        "date": date_val.isoformat(),
        "opening_balance": opening_balance,
        "total_receipts": total_receipts,
        "total_payments": total_payments,
        "closing_balance": closing_balance,
        "transactions": transactions_list,
    }


def _resolve_fiscal_year(
    institution: "Institution", fiscal_year: FiscalYear | None = None
) -> FiscalYear:
    if fiscal_year is not None:
        return fiscal_year
    fy = (
        FiscalYear.objects.filter(institution=institution, is_current=True).first()
        or FiscalYear.objects.filter(institution=institution).order_by("-start_date").first()
    )
    if not fy:
        raise ValueError("No fiscal year found for institution.")
    return fy


def get_trial_balance(
    institution: "Institution",
    as_of_date: date | None = None,
    fiscal_year: FiscalYear | None = None,
) -> dict[str, Any]:
    """Generate Trial Balance (রেওয়ামিল) verifying debits equal credits."""
    fy = _resolve_fiscal_year(institution, fiscal_year)

    filter_kwargs: dict[str, Any] = {
        "institution": institution,
        "entry__status": VoucherStatus.POSTED,
    }
    if as_of_date:
        filter_kwargs["entry__date__lte"] = as_of_date
    else:
        filter_kwargs["entry__fiscal_year"] = fy

    accounts = Account.objects.filter(institution=institution, is_group=False).order_by(
        "account_code"
    )
    account_rows = []
    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")

    for acc in accounts:
        dr = acc.journal_items.filter(**filter_kwargs).aggregate(total=Sum("debit"))[
            "total"
        ] or Decimal("0.00")
        cr = acc.journal_items.filter(**filter_kwargs).aggregate(total=Sum("credit"))[
            "total"
        ] or Decimal("0.00")

        # Compute net trial balance debit or credit
        if acc.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            net = acc.opening_balance + dr - cr
            net_dr = net if net > Decimal("0.00") else Decimal("0.00")
            net_cr = abs(net) if net < Decimal("0.00") else Decimal("0.00")
        else:
            net = acc.opening_balance + cr - dr
            net_cr = net if net > Decimal("0.00") else Decimal("0.00")
            net_dr = abs(net) if net < Decimal("0.00") else Decimal("0.00")

        if (
            net_dr > Decimal("0.00")
            or net_cr > Decimal("0.00")
            or acc.opening_balance > Decimal("0.00")
        ):
            account_rows.append(
                {
                    "account_code": acc.account_code,
                    "name_en": acc.name_en,
                    "name_bn": acc.name_bn,
                    "account_type": acc.account_type,
                    "debit": net_dr,
                    "credit": net_cr,
                }
            )
            total_debits += net_dr
            total_credits += net_cr

    is_balanced = total_debits == total_credits

    return {
        "fiscal_year": fy.name,
        "as_of_date": as_of_date.isoformat() if as_of_date else fy.end_date.isoformat(),
        "accounts": account_rows,
        "total_debit": total_debits,
        "total_credit": total_credits,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "is_balanced": is_balanced,
    }


def get_income_statement(
    institution: "Institution",
    start_date: date | None = None,
    end_date: date | None = None,
    fiscal_year: FiscalYear | None = None,
) -> dict[str, Any]:
    """Generate Income & Expenditure Statement (লাভ-ক্ষতি / আয়-ব্যয় বিবরণী)."""
    fy = _resolve_fiscal_year(institution, fiscal_year)

    filter_kwargs: dict[str, Any] = {
        "institution": institution,
        "entry__status": VoucherStatus.POSTED,
    }
    if start_date and end_date:
        filter_kwargs["entry__date__gte"] = start_date
        filter_kwargs["entry__date__lte"] = end_date
    else:
        filter_kwargs["entry__fiscal_year"] = fy

    # 1. Incomes (AccountType.INCOME): Credit - Debit
    incomes = Account.objects.filter(
        institution=institution, account_type=AccountType.INCOME, is_group=False
    ).order_by("account_code")
    income_rows = []
    total_income = Decimal("0.00")

    for acc in incomes:
        cr = acc.journal_items.filter(**filter_kwargs).aggregate(t=Sum("credit"))["t"] or Decimal(
            "0.00"
        )
        dr = acc.journal_items.filter(**filter_kwargs).aggregate(t=Sum("debit"))["t"] or Decimal(
            "0.00"
        )
        amt = cr - dr
        if amt != Decimal("0.00"):
            income_rows.append(
                {"account_code": acc.account_code, "name_en": acc.name_en, "amount": amt}
            )
            total_income += amt

    # 2. Expenses (AccountType.EXPENSE): Debit - Credit
    expenses = Account.objects.filter(
        institution=institution, account_type=AccountType.EXPENSE, is_group=False
    ).order_by("account_code")
    expense_rows = []
    total_expense = Decimal("0.00")

    for acc in expenses:
        dr = acc.journal_items.filter(**filter_kwargs).aggregate(t=Sum("debit"))["t"] or Decimal(
            "0.00"
        )
        cr = acc.journal_items.filter(**filter_kwargs).aggregate(t=Sum("credit"))["t"] or Decimal(
            "0.00"
        )
        amt = dr - cr
        if amt != Decimal("0.00"):
            expense_rows.append(
                {"account_code": acc.account_code, "name_en": acc.name_en, "amount": amt}
            )
            total_expense += amt

    net_surplus = total_income - total_expense

    return {
        "fiscal_year": fy.name,
        "start_date": (start_date or fy.start_date).isoformat(),
        "end_date": (end_date or fy.end_date).isoformat(),
        "incomes": income_rows,
        "total_income": total_income,
        "expenses": expense_rows,
        "total_expense": total_expense,
        "net_surplus": net_surplus,
        "is_surplus": net_surplus >= Decimal("0.00"),
    }


def get_balance_sheet(
    institution: "Institution",
    as_of_date: date | None = None,
    fiscal_year: FiscalYear | None = None,
) -> dict[str, Any]:
    """Generate Balance Sheet (আর্থিক অবস্থার বিবরণী): Assets = Liabilities + Equity."""
    fy = _resolve_fiscal_year(institution, fiscal_year)
    filter_date = as_of_date or fy.end_date

    # Helper to calculate net balance up to filter_date
    def calc_net(acc: Account) -> Decimal:
        dr = acc.journal_items.filter(
            entry__status=VoucherStatus.POSTED, entry__date__lte=filter_date
        ).aggregate(t=Sum("debit"))["t"] or Decimal("0.00")
        cr = acc.journal_items.filter(
            entry__status=VoucherStatus.POSTED, entry__date__lte=filter_date
        ).aggregate(t=Sum("credit"))["t"] or Decimal("0.00")
        if acc.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            return acc.opening_balance + dr - cr
        return acc.opening_balance + cr - dr

    # 1. Assets
    asset_accounts = Account.objects.filter(
        institution=institution, account_type=AccountType.ASSET, is_group=False
    ).order_by("account_code")
    asset_rows = []
    total_assets = Decimal("0.00")
    for acc in asset_accounts:
        bal = calc_net(acc)
        if bal != Decimal("0.00"):
            asset_rows.append(
                {"account_code": acc.account_code, "name_en": acc.name_en, "balance": bal}
            )
            total_assets += bal

    # 2. Liabilities
    liability_accounts = Account.objects.filter(
        institution=institution, account_type=AccountType.LIABILITY, is_group=False
    ).order_by("account_code")
    liability_rows = []
    total_liabilities = Decimal("0.00")
    for acc in liability_accounts:
        bal = calc_net(acc)
        if bal != Decimal("0.00"):
            liability_rows.append(
                {"account_code": acc.account_code, "name_en": acc.name_en, "balance": bal}
            )
            total_liabilities += bal

    # 3. Equity & Fund Balances + Period Retained Surplus
    equity_accounts = Account.objects.filter(
        institution=institution, account_type=AccountType.EQUITY, is_group=False
    ).order_by("account_code")
    equity_rows = []
    total_equity = Decimal("0.00")
    for acc in equity_accounts:
        bal = calc_net(acc)
        if bal != Decimal("0.00"):
            equity_rows.append(
                {"account_code": acc.account_code, "name_en": acc.name_en, "balance": bal}
            )
            total_equity += bal

    # Retained Surplus from operations
    income_stmt = get_income_statement(
        institution, start_date=fy.start_date, end_date=filter_date, fiscal_year=fy
    )
    period_surplus = income_stmt["net_surplus"]
    total_equity += period_surplus
    equity_rows.append(
        {
            "account_code": "SURPLUS",
            "name_en": "Current Period Surplus / (Deficit)",
            "balance": period_surplus,
        }
    )

    total_liabilities_and_equity = total_liabilities + total_equity
    is_balanced = total_assets == total_liabilities_and_equity

    return {
        "fiscal_year": fy.name,
        "as_of_date": filter_date.isoformat(),
        "assets": asset_rows,
        "total_assets": total_assets,
        "liabilities": liability_rows,
        "total_liabilities": total_liabilities,
        "equity": equity_rows,
        "total_equity": total_equity,
        "total_liabilities_and_equity": total_liabilities_and_equity,
        "is_balanced": is_balanced,
    }
