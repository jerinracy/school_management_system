"""Accounting models: Fiscal years, Chart of Accounts, Vouchers, and Cashbook."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class FiscalYear(TenantOwnedModel):
    """Financial year cycle for school accounting (e.g. July 1 - June 30 or Jan 1 - Dec 31)."""

    name = models.CharField(max_length=100, help_text="e.g. FY 2025-2026 or 2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates the active operating fiscal year for the institution.",
    )
    is_closed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Closed fiscal years prohibit further voucher posting.",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Fiscal Year"
        verbose_name_plural = "Fiscal Years"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_fiscal_year_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date.year}-{self.end_date.year})"

    def save(self, *args, **kwargs):
        if self.is_current:
            FiscalYear.objects.filter(institution=self.institution, is_current=True).exclude(
                pk=self.pk
            ).update(is_current=False)
        super().save(*args, **kwargs)


class AccountType(models.TextChoices):
    ASSET = "asset", "Asset (সম্পদ)"
    LIABILITY = "liability", "Liability (দায়)"
    EQUITY = "equity", "Equity / Fund Balance (মূলধন / তহবিল)"
    INCOME = "income", "Income / Revenue (আয়)"
    EXPENSE = "expense", "Expense (ব্যয়)"


class AccountSubtype(models.TextChoices):
    CASH = "cash", "Cash in Hand (নগদ টাকা)"
    BANK = "bank", "Bank Account (ব্যাংক হিসাব)"
    MFS = "mfs", "Mobile Financial Services / Gateway (বিকাশ / নগদ)"
    RECEIVABLE = "receivable", "Accounts Receivable (প্রাপ্য হিসাব)"
    PAYABLE = "payable", "Accounts Payable (প্রদেয় হিসাব)"
    CURRENT_ASSET = "current_asset", "Other Current Asset"
    FIXED_ASSET = "fixed_asset", "Fixed Asset (স্থায়ী সম্পদ)"
    CURRENT_LIABILITY = "current_liability", "Current Liability"
    LONG_TERM_LIABILITY = "long_term_liability", "Long-term Liability"
    GENERAL_FUND = "general_fund", "General Fund"
    DEVELOPMENT_FUND = "development_fund", "Development / Building Fund"
    SCHOLARSHIP_FUND = "scholarship_fund", "Scholarship / Poor Fund"
    TUITION_FEE = "tuition_fee", "Tuition Fee Revenue"
    ADMISSION_FEE = "admission_fee", "Admission Fee Revenue"
    EXAM_FEE = "exam_fee", "Exam Fee Revenue"
    OTHER_INCOME = "other_income", "Other Operating Income"
    SALARY_EXPENSE = "salary_expense", "Staff Salary & Allowances"
    UTILITY_EXPENSE = "utility_expense", "Utility (Electricity, Water, Internet)"
    EXAM_EXPENSE = "exam_expense", "Exam & Evaluation Expenses"
    MAINTENANCE_EXPENSE = "maintenance_expense", "Repairs & Maintenance"
    ADMIN_EXPENSE = "admin_expense", "Administrative & Office Expense"
    OTHER_EXPENSE = "other_expense", "Other Expense"


class Account(TenantOwnedModel, SoftDeleteMixin):
    """Chart of Accounts (COA) hierarchical general ledger node."""

    account_code = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Standardized code (e.g. 1010 for Cash, 4010 for Tuition Fee).",
    )
    name_en = models.CharField(max_length=200, help_text="Account title in English.")
    name_bn = models.CharField(max_length=200, blank=True, help_text="Account title in Bengali.")
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        db_index=True,
    )
    subtype = models.CharField(
        max_length=30,
        choices=AccountSubtype.choices,
        blank=True,
        default="",
        db_index=True,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        help_text="Parent account grouping for tree hierarchy.",
    )
    is_group = models.BooleanField(
        default=False,
        help_text="If True, acts as a header folder and cannot receive direct voucher postings.",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System-locked default account that cannot be deleted.",
    )
    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Starting balance at the inception of the account.",
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Running net balance derived from posted vouchers.",
    )
    bank_name = models.CharField(max_length=100, blank=True, help_text="e.g. Sonali Bank PLC")
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Account"
        verbose_name_plural = "Chart of Accounts"
        ordering = ["account_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "account_code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_account_code_per_institution",
            )
        ]

    @property
    def normal_balance(self) -> str:
        """Return normal balance type for this account: 'debit' or 'credit'."""
        if self.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            return "debit"
        return "credit"

    def __str__(self) -> str:
        return f"{self.account_code} - {self.name_en}"


class VoucherType(models.TextChoices):
    JOURNAL = "journal", "Journal Voucher (JV) (জাবেদা)"
    PAYMENT = "payment", "Payment Voucher (PV) (ডেবিট / খরচ)"
    RECEIPT = "receipt", "Receipt Voucher (RV) (ক্রেডিট / জমা)"
    CONTRA = "contra", "Contra Voucher (CV) (কন্ট্রা / স্থানান্তর)"


class VoucherStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    POSTED = "posted", "Posted"
    VOID = "void", "Void"


class VoucherSequence(TenantOwnedModel):
    """Atomic gap-free sequential counter for accounting vouchers."""

    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name="voucher_sequences",
    )
    voucher_type = models.CharField(
        max_length=20,
        choices=VoucherType.choices,
    )
    last_number = models.PositiveIntegerField(default=0)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Voucher Sequence"
        verbose_name_plural = "Voucher Sequences"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "fiscal_year", "voucher_type"],
                name="unique_voucher_sequence_per_year_and_type",
            )
        ]


class JournalEntry(TenantOwnedModel, SoftDeleteMixin):
    """Header record for double-entry financial vouchers."""

    voucher_no = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Formatted sequence number, e.g. PV-2026-000001",
    )
    voucher_type = models.CharField(
        max_length=20,
        choices=VoucherType.choices,
        default=VoucherType.JOURNAL,
        db_index=True,
    )
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )
    date = models.DateField(default=timezone.now, db_index=True)
    narration = models.TextField(help_text="Purpose and explanation of the transaction.")
    status = models.CharField(
        max_length=20,
        choices=VoucherStatus.choices,
        default=VoucherStatus.DRAFT,
        db_index=True,
    )
    cheque_no = models.CharField(max_length=50, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    payee_or_payer = models.CharField(
        max_length=200,
        blank=True,
        help_text="Person or entity receiving or providing payment.",
    )
    total_debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True, default="")
    payment_reference = models.ForeignKey(
        "fees.Payment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
        help_text="Linked fee payment transaction if automatically generated.",
    )
    attachment = models.FileField(upload_to="accounting/vouchers/", blank=True, null=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "voucher_no"],
                name="unique_voucher_no_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.voucher_no} ({self.get_voucher_type_display()}) - ৳{self.total_debit}"


class JournalEntryItem(TenantOwnedModel):
    """Line item split debit/credit row in a voucher."""

    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="items",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_items",
    )
    debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    narration = models.CharField(max_length=255, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Journal Entry Item"
        verbose_name_plural = "Journal Entry Items"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.account.account_code}: DR ৳{self.debit} | CR ৳{self.credit}"


class Budget(TenantOwnedModel):
    """Annual budgetary allocation for expense and revenue accounts."""

    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="budgets",
    )
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    spent_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    note = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "fiscal_year", "account"],
                name="unique_budget_per_year_and_account",
            )
        ]


class CashbookClosing(TenantOwnedModel):
    """Daily closing reconciliation for cash-in-hand and bank drawer balances."""

    date = models.DateField(db_index=True)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="cashbook_closings",
        help_text="Cash or Bank account being reconciled.",
    )
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2)
    total_receipts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_payments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2)
    physical_count = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Physical currency denomination count in drawer.",
    )
    discrepancy = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Variance: physical_count - closing_balance (shortage or excess).",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    note = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Cashbook Closing"
        verbose_name_plural = "Cashbook Closings"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "account", "date"],
                name="unique_cashbook_closing_per_account_and_date",
            )
        ]
