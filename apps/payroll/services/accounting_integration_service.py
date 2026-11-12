"""General Ledger integration posting balanced payroll vouchers into apps.accounting."""

import logging
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, VoucherStatus, VoucherType
from apps.accounting.services.account_service import seed_default_chart_of_accounts
from apps.accounting.services.voucher_service import create_journal_entry
from apps.accounts.models import User
from apps.payroll.models import PayrollRun, PayrollRunStatus, Payslip, SalaryPaymentMethod
from apps.payroll.services.payroll_calculator import q2

logger = logging.getLogger(__name__)


def _get_or_seed_account(institution: Any, account_code: str) -> Account:
    """Resolve an active non-group COA account by code, seeding defaults if needed."""
    account = Account.objects.filter(
        institution=institution,
        account_code=account_code,
        is_deleted=False,
        is_group=False,
    ).first()
    if account:
        return account

    seed_default_chart_of_accounts(institution)
    account = Account.objects.filter(
        institution=institution,
        account_code=account_code,
        is_deleted=False,
        is_group=False,
    ).first()
    if not account:
        raise ValidationError(
            f"Required General Ledger account '{account_code}' is missing or is a group account."
        )
    return account


def _aggregate_gl_amounts(payslips: list[Payslip]) -> dict[str, Decimal]:
    """Compute balanced earned gross, net disbursement splits, PF, and withheld liabilities."""
    earned_gross = Decimal("0.00")
    total_net_pay = Decimal("0.00")
    cash_net_pay = Decimal("0.00")
    bank_net_pay = Decimal("0.00")
    total_employer_pf = Decimal("0.00")

    for slip in payslips:
        slip_earned = max(Decimal("0.00"), q2(slip.gross_earnings - slip.absence_deduction_amount))
        earned_gross += slip_earned
        total_net_pay += slip.net_payable
        total_employer_pf += slip.pf_employer_amount
        if slip.payment_method == SalaryPaymentMethod.CASH:
            cash_net_pay += slip.net_payable
        else:
            bank_net_pay += slip.net_payable

    earned_gross = q2(earned_gross)
    total_net_pay = q2(total_net_pay)
    total_employer_pf = q2(total_employer_pf)
    total_withheld = q2(earned_gross - total_net_pay)
    if total_withheld < Decimal("0.00"):
        earned_gross = q2(earned_gross - total_withheld)
        total_withheld = Decimal("0.00")

    return {
        "earned_gross": earned_gross,
        "cash_net_pay": q2(cash_net_pay),
        "bank_net_pay": q2(bank_net_pay),
        "total_employer_pf": total_employer_pf,
        "total_liability_credit": q2(total_withheld + total_employer_pf),
    }


def _build_payroll_gl_items(
    payroll_run: PayrollRun,
    totals: dict[str, Decimal],
    accounts: dict[str, Account],
) -> list[dict[str, Any]]:
    """Assemble balanced debit and credit voucher lines for a PayrollRun."""
    period = f"{payroll_run.year}-{payroll_run.month:02d}"
    candidates = [
        (
            totals["earned_gross"],
            accounts["expense"],
            True,
            f"Staff Salaries & Allowances ({period})",
        ),
        (
            totals["total_employer_pf"],
            accounts["expense"],
            True,
            f"Employer Provident Fund Contribution ({period})",
        ),
        (
            totals["bank_net_pay"],
            accounts["bank"],
            False,
            f"Net Salary Disbursement - Bank/BEFTN/MFS ({period})",
        ),
        (
            totals["cash_net_pay"],
            accounts["cash"],
            False,
            f"Net Salary Disbursement - Cash ({period})",
        ),
        (
            totals["total_liability_credit"],
            accounts["liability"],
            False,
            f"Withheld PF, TDS & Loan Recoveries ({period})",
        ),
    ]
    return [
        {
            "account": acct,
            "debit": amt if is_debit else Decimal("0.00"),
            "credit": Decimal("0.00") if is_debit else amt,
            "description": desc,
        }
        for amt, acct, is_debit, desc in candidates
        if amt > Decimal("0.00")
    ]


@transaction.atomic
def post_payroll_to_accounting(
    payroll_run: PayrollRun,
    user: User,
    posting_date: Any = None,
    bank_account_code: str = "1021",
    cash_account_code: str = "1010",
    salary_expense_code: str = "5010",
    liability_account_code: str = "2030",
) -> JournalEntry:
    """Create and post a balanced JournalEntry for an approved/paid PayrollRun."""
    if payroll_run.status not in (
        PayrollRunStatus.APPROVED,
        PayrollRunStatus.PAID,
        PayrollRunStatus.LOCKED,
    ):
        raise ValidationError(
            f"Payroll run must be APPROVED, PAID, or LOCKED before GL posting (current: {payroll_run.status})."
        )

    if (
        payroll_run.journal_entry is not None
        and payroll_run.journal_entry.status != VoucherStatus.VOID
    ):
        raise ValidationError(
            f"Payroll run is already posted to voucher {payroll_run.journal_entry.voucher_no}."
        )

    payslips = list(payroll_run.payslips.all())
    if not payslips:
        raise ValidationError("Cannot post payroll run with no payslips to General Ledger.")

    totals = _aggregate_gl_amounts(payslips)
    accounts = {
        "expense": _get_or_seed_account(payroll_run.institution, salary_expense_code),
        "bank": _get_or_seed_account(payroll_run.institution, bank_account_code),
        "cash": _get_or_seed_account(payroll_run.institution, cash_account_code),
        "liability": _get_or_seed_account(payroll_run.institution, liability_account_code),
    }
    items = _build_payroll_gl_items(payroll_run, totals, accounts)

    entry = create_journal_entry(
        institution=payroll_run.institution,
        voucher_type=VoucherType.PAYMENT,
        date=posting_date or timezone.localdate(),
        narration=f"Monthly Payroll Posting - {payroll_run.title or f'{payroll_run.year}-{payroll_run.month:02d}'}",
        items=items,
        user=user,
        payee_or_payer="Institution Staff Payroll",
        auto_post=True,
    )

    payroll_run.journal_entry = entry
    payroll_run.save(update_fields=["journal_entry", "updated_at"])
    logger.info("PayrollRun %s posted to GL voucher %s", payroll_run.id, entry.voucher_no)
    return entry
