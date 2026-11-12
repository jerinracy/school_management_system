"""Integration service linking Fees/Payments (Task 15) to General Ledger vouchers."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from apps.accounting.models import (
    Account,
    AccountSubtype,
    AccountType,
    FiscalYear,
    JournalEntry,
    VoucherType,
)
from apps.accounting.services.account_service import seed_default_chart_of_accounts
from apps.accounting.services.voucher_service import create_journal_entry

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.fees.models import Payment

logger = logging.getLogger(__name__)


def get_or_create_active_fiscal_year(institution) -> FiscalYear:
    """Retrieve the current active fiscal year or create one for the current year."""
    fy = FiscalYear.objects.filter(institution=institution, is_current=True).first()
    if not fy:
        from django.utils import timezone

        now = timezone.now().date()
        fy, _ = FiscalYear.objects.get_or_create(
            institution=institution,
            name=f"FY {now.year}",
            defaults={
                "start_date": f"{now.year}-01-01",
                "end_date": f"{now.year}-12-31",
                "is_current": True,
            },
        )
    return fy


def resolve_asset_account_for_payment(institution, payment: "Payment") -> Account:
    """Find appropriate Cash, Bank, or MFS asset account based on payment method."""
    method = payment.payment_method.lower()
    if method == "cash":
        acc = Account.objects.filter(
            institution=institution,
            subtype=AccountSubtype.CASH,
            is_group=False,
            is_active=True,
        ).first()
        code = "1010"
    elif method in ("bkash", "mfs"):
        acc = Account.objects.filter(
            institution=institution,
            account_code="1031",
            is_group=False,
        ).first()
        code = "1031"
    elif method == "nagad":
        acc = Account.objects.filter(
            institution=institution,
            account_code="1032",
            is_group=False,
        ).first()
        code = "1032"
    elif method in ("sslcommerz", "aamarpay"):
        acc = Account.objects.filter(
            institution=institution,
            account_code="1033",
            is_group=False,
        ).first()
        code = "1033"
    else:  # bank, cheque, pos card
        acc = Account.objects.filter(
            institution=institution,
            subtype=AccountSubtype.BANK,
            is_group=False,
            is_active=True,
        ).first()
        code = "1021"

    if not acc:
        seed_default_chart_of_accounts(institution)
        acc = (
            Account.objects.filter(
                institution=institution,
                account_code=code,
            ).first()
            or Account.objects.filter(institution=institution, is_group=False).first()
        )

    assert acc is not None
    return acc


def create_voucher_for_fee_payment(payment: "Payment", user: "User | None" = None) -> JournalEntry:
    """Automatically generate and post a Receipt Voucher (RV) for a settled fee payment."""
    institution = payment.institution
    fy = get_or_create_active_fiscal_year(institution)
    debit_account = resolve_asset_account_for_payment(institution, payment)

    items_data: list[dict] = []
    total_payment = payment.amount

    # 1. Debit Asset Account (Cash/Bank/MFS)
    items_data.append(
        {
            "account": debit_account,
            "debit": total_payment,
            "credit": Decimal("0.00"),
            "narration": f"Payment from {payment.student.name_en} ({payment.payment_method.upper()})",
        }
    )

    # 2. Credit Revenue or Advance accounts based on allocations
    allocated_sum = Decimal("0.00")
    allocations = list(payment.allocations.select_related("invoice_line__fee_head").all())

    if allocations:
        for alloc in allocations:
            fee_head = alloc.invoice_line.fee_head if alloc.invoice_line else None
            account_code = (fee_head.account_code if fee_head else None) or "4010"
            credit_acc = Account.objects.filter(
                institution=institution,
                account_code=account_code,
                is_group=False,
            ).first()

            if not credit_acc:
                credit_acc = Account.objects.filter(
                    institution=institution,
                    account_type=AccountType.INCOME,
                    is_group=False,
                ).first()

            if not credit_acc:
                seed_default_chart_of_accounts(institution)
                credit_acc = Account.objects.filter(
                    institution=institution,
                    account_code="4010",
                ).first()

            assert credit_acc is not None
            head_name = fee_head.name_en if fee_head else "Tuition"
            items_data.append(
                {
                    "account": credit_acc,
                    "debit": Decimal("0.00"),
                    "credit": alloc.allocated_amount,
                    "narration": f"Fee Revenue: {head_name}",
                }
            )
            allocated_sum += alloc.allocated_amount

        # Surplus overpayment credited to Student Advance Balances (2010)
        surplus = total_payment - allocated_sum
        if surplus > Decimal("0.00"):
            advance_acc = Account.objects.filter(
                institution=institution,
                account_code="2010",
                is_group=False,
            ).first()
            if not advance_acc:
                advance_acc = Account.objects.filter(
                    institution=institution,
                    account_type=AccountType.LIABILITY,
                    is_group=False,
                ).first()

            assert advance_acc is not None
            items_data.append(
                {
                    "account": advance_acc,
                    "debit": Decimal("0.00"),
                    "credit": surplus,
                    "narration": f"Student Advance Deposit: {payment.student.name_en}",
                }
            )
    else:
        # Lump sum payment without line-item allocations: credit Tuition Fee income directly
        fallback_acc = (
            Account.objects.filter(
                institution=institution,
                account_code="4010",
                is_group=False,
            ).first()
            or Account.objects.filter(
                institution=institution, account_type=AccountType.INCOME, is_group=False
            ).first()
        )

        if not fallback_acc:
            seed_default_chart_of_accounts(institution)
            fallback_acc = Account.objects.filter(
                institution=institution,
                account_code="4010",
            ).first()

        assert fallback_acc is not None
        items_data.append(
            {
                "account": fallback_acc,
                "debit": Decimal("0.00"),
                "credit": total_payment,
                "narration": f"Tuition collection: {payment.student.name_en}",
            }
        )

    with transaction.atomic():
        entry = create_journal_entry(
            institution=institution,
            fiscal_year=fy,
            voucher_type=VoucherType.RECEIPT,
            date=payment.payment_date.date(),
            narration=f"Fee Collection: Receipt for student {payment.student.name_en} ({payment.student.student_id})",
            items_data=items_data,
            user=user,
            auto_post=True,
            payment_ref=payment,
            payee_or_payer=payment.student.name_en,
        )

    logger.info("Generated RV voucher %s for payment %s", entry.voucher_no, payment.id)
    return entry
