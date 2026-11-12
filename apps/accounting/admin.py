"""Django admin configuration for accounting models."""

from django.contrib import admin

from apps.accounting.models import (
    Account,
    Budget,
    CashbookClosing,
    FiscalYear,
    JournalEntry,
    JournalEntryItem,
    VoucherSequence,
)


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "start_date", "end_date", "is_current", "is_closed"]
    list_filter = ["is_current", "is_closed", "institution"]
    search_fields = ["name"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        "account_code",
        "name_en",
        "name_bn",
        "account_type",
        "subtype",
        "parent",
        "is_group",
        "current_balance",
        "institution",
    ]
    list_filter = ["account_type", "subtype", "is_group", "is_system", "institution"]
    search_fields = ["account_code", "name_en", "name_bn"]
    ordering = ["account_code"]


class JournalEntryItemInline(admin.TabularInline):
    model = JournalEntryItem
    extra = 2
    fields = ["account", "debit", "credit", "narration"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = [
        "voucher_no",
        "voucher_type",
        "date",
        "status",
        "total_debit",
        "total_credit",
        "institution",
    ]
    list_filter = ["voucher_type", "status", "institution", "date"]
    search_fields = ["voucher_no", "narration", "cheque_no", "payment_reference"]
    inlines = [JournalEntryItemInline]


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["account", "fiscal_year", "allocated_amount", "spent_amount", "institution"]
    list_filter = ["fiscal_year", "institution"]
    search_fields = ["account__name_en", "account__account_code"]


@admin.register(CashbookClosing)
class CashbookClosingAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "account",
        "opening_balance",
        "total_receipts",
        "total_payments",
        "closing_balance",
        "physical_count",
        "discrepancy",
        "institution",
    ]
    list_filter = ["institution", "date"]


@admin.register(VoucherSequence)
class VoucherSequenceAdmin(admin.ModelAdmin):
    list_display = ["institution", "fiscal_year", "voucher_type", "last_number"]
    list_filter = ["voucher_type", "institution"]
