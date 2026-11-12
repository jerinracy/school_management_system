"""Double-entry voucher processing service."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import (
    Account,
    AccountType,
    FiscalYear,
    JournalEntry,
    JournalEntryItem,
    VoucherSequence,
    VoucherStatus,
    VoucherType,
)

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.institutions.models import Institution

logger = logging.getLogger(__name__)

VOUCHER_PREFIXES = {
    VoucherType.JOURNAL: "JV",
    VoucherType.PAYMENT: "PV",
    VoucherType.RECEIPT: "RV",
    VoucherType.CONTRA: "CV",
    "JV": "JV",
    "PV": "PV",
    "RV": "RV",
    "CV": "CV",
}


def get_next_voucher_number(
    institution: "Institution",
    fiscal_year: FiscalYear,
    voucher_type: str,
) -> str:
    """Generate the next sequential, gap-free voucher number atomically."""
    # Normalize voucher type if passed as shorthand (e.g. PV -> payment)
    shorthand_map = {
        "JV": VoucherType.JOURNAL,
        "PV": VoucherType.PAYMENT,
        "RV": VoucherType.RECEIPT,
        "CV": VoucherType.CONTRA,
    }
    v_type = shorthand_map.get(voucher_type, voucher_type)

    with transaction.atomic():
        seq, _ = VoucherSequence.objects.select_for_update().get_or_create(
            institution=institution,
            fiscal_year=fiscal_year,
            voucher_type=v_type,
            defaults={"last_number": 0},
        )
        seq.last_number += 1
        seq.save(update_fields=["last_number"])

        prefix = VOUCHER_PREFIXES.get(v_type, "VOUCHER")
        year_str = str(fiscal_year.start_date.year)
        return f"{prefix}-{year_str}-{seq.last_number:06d}"


def _resolve_voucher_fiscal_year(
    institution: "Institution", entry_date: Any, fiscal_year: FiscalYear | None
) -> FiscalYear:
    """Resolve and validate the fiscal year for voucher posting."""
    if fiscal_year is None:
        fiscal_year = (
            FiscalYear.objects.filter(institution=institution, is_current=True).first()
            or FiscalYear.objects.filter(
                institution=institution,
                start_date__lte=entry_date,
                end_date__gte=entry_date,
            ).first()
            or FiscalYear.objects.filter(institution=institution).order_by("-start_date").first()
        )
    if not fiscal_year:
        raise ValidationError("No active fiscal year found for institution.")
    if fiscal_year.is_closed:
        raise ValidationError(f"Fiscal year '{fiscal_year.name}' is closed. No entries permitted.")
    return fiscal_year


def _validate_and_sum_items(items: list[dict[str, Any]]) -> Decimal:
    """Validate double-entry balancing and return total balanced amount."""
    if not items or len(items) < 2:
        raise ValidationError("A voucher must contain at least two line items (debit and credit).")

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for item in items:
        d = Decimal(str(item.get("debit", 0) or 0))
        c = Decimal(str(item.get("credit", 0) or 0))
        if d < 0 or c < 0:
            raise ValidationError("Line items cannot have negative amounts.")
        total_debit += d
        total_credit += c

    if total_debit <= Decimal("0.00") or total_credit <= Decimal("0.00"):
        raise ValidationError("Voucher total debit and credit must be greater than zero.")
    if total_debit != total_credit:
        raise ValidationError(
            f"Voucher out of balance! Total debits (৳{total_debit}) must equal total credits (৳{total_credit})."
        )
    return total_debit


def create_journal_entry(
    institution: "Institution",
    voucher_type: str,
    narration: str,
    date: Any = None,
    fiscal_year: FiscalYear | None = None,
    items: list[dict[str, Any]] | None = None,
    items_data: list[dict[str, Any]] | None = None,
    user: "User | None" = None,
    created_by: "User | None" = None,
    auto_post: bool = False,
    payment_ref: Any = None,
    payment_reference: Any = None,
    cheque_no: str = "",
    cheque_date: Any = None,
    payee_or_payer: str = "",
    attachment: Any = None,
) -> JournalEntry:
    """Create a balanced double-entry voucher."""
    entry_date = date or timezone.now().date()
    fiscal_year = _resolve_voucher_fiscal_year(institution, entry_date, fiscal_year)

    effective_items = items_data if items_data is not None else items or []
    total_amount = _validate_and_sum_items(effective_items)

    effective_user = user or created_by
    effective_payment_ref = payment_ref or payment_reference
    payment_obj = None
    if effective_payment_ref is not None:
        from apps.fees.models import Payment

        if isinstance(effective_payment_ref, Payment):
            payment_obj = effective_payment_ref
        elif isinstance(effective_payment_ref, (str, int)):
            payment_obj = Payment.objects.filter(id=str(effective_payment_ref)).first()

    shorthand_map = {
        "JV": VoucherType.JOURNAL,
        "PV": VoucherType.PAYMENT,
        "RV": VoucherType.RECEIPT,
        "CV": VoucherType.CONTRA,
    }
    v_type = shorthand_map.get(voucher_type, voucher_type)

    with transaction.atomic():
        voucher_no = get_next_voucher_number(institution, fiscal_year, v_type)
        entry = JournalEntry.objects.create(
            institution=institution,
            voucher_no=voucher_no,
            voucher_type=v_type,
            fiscal_year=fiscal_year,
            date=entry_date,
            narration=narration.strip(),
            status=VoucherStatus.DRAFT,
            cheque_no=cheque_no,
            cheque_date=cheque_date,
            payee_or_payer=payee_or_payer,
            total_debit=total_amount,
            total_credit=total_amount,
            created_by=effective_user,
            payment_reference=payment_obj,
            attachment=attachment,
        )

        for item in effective_items:
            account = item["account"]
            if isinstance(account, (str, int)):
                account = Account.objects.get(id=str(account), institution=institution)

            if account.is_group:
                raise ValidationError(
                    f"Account '{account.account_code} - {account.name_en}' is a group account and cannot receive direct postings."
                )

            JournalEntryItem.objects.create(
                institution=institution,
                entry=entry,
                account=account,
                debit=Decimal(str(item.get("debit", 0) or 0)),
                credit=Decimal(str(item.get("credit", 0) or 0)),
                narration=item.get("narration", ""),
            )

        if auto_post:
            entry = post_journal_entry(entry, effective_user)

    return entry


def post_journal_entry(entry: JournalEntry, user: "User | None") -> JournalEntry:
    """Post a draft voucher to the General Ledger, adjusting account balances."""
    if entry.status == VoucherStatus.POSTED:
        return entry

    if entry.status == VoucherStatus.VOID:
        raise ValidationError("Cannot post a voided voucher.")

    if entry.fiscal_year.is_closed:
        raise ValidationError("Cannot post to a closed fiscal year.")

    with transaction.atomic():
        # Lock entry
        entry = JournalEntry.objects.select_for_update().get(id=entry.id)
        if entry.status == VoucherStatus.POSTED:
            return entry

        # Iterate items and update account balances
        for item in entry.items.select_related("account").all():
            account = Account.objects.select_for_update().get(id=item.account.id)
            if account.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                # Normal debit balance: +debit, -credit
                account.current_balance += item.debit - item.credit
            else:
                # Normal credit balance (Liability, Equity, Income): +credit, -debit
                account.current_balance += item.credit - item.debit
            account.save(update_fields=["current_balance", "updated_at"])

        entry.status = VoucherStatus.POSTED
        entry.posted_at = timezone.now()
        entry.posted_by = user
        entry.save(update_fields=["status", "posted_at", "posted_by", "updated_at"])

        logger.info("Posted voucher %s (total: ৳%s)", entry.voucher_no, entry.total_debit)

    return entry


def void_journal_entry(entry: JournalEntry, user: "User | None", reason: str = "") -> JournalEntry:
    """Void a posted or draft voucher, reversing all balances if previously posted."""
    if entry.status == VoucherStatus.VOID:
        return entry

    with transaction.atomic():
        entry = JournalEntry.objects.select_for_update().get(id=entry.id)
        if entry.status == VoucherStatus.VOID:
            return entry

        # If it was posted, reverse the GL impact
        if entry.status == VoucherStatus.POSTED:
            for item in entry.items.select_related("account").all():
                account = Account.objects.select_for_update().get(id=item.account.id)
                if account.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                    # Reverse: -debit, +credit
                    account.current_balance -= item.debit - item.credit
                else:
                    # Reverse: -credit, +debit
                    account.current_balance -= item.credit - item.debit
                account.save(update_fields=["current_balance", "updated_at"])

        entry.status = VoucherStatus.VOID
        entry.voided_at = timezone.now()
        entry.voided_by = user
        entry.void_reason = reason.strip()
        entry.save(update_fields=["status", "voided_at", "voided_by", "void_reason", "updated_at"])

        logger.info("Voided voucher %s. Reason: %s", entry.voucher_no, reason)

    return entry
