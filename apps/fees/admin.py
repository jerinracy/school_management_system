"""Django admin configurations for Fee Management."""

from django.contrib import admin

from apps.fees.models import (
    AdvanceBalance,
    AdvanceTransaction,
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FineRule,
    Invoice,
    InvoiceLine,
    InvoiceSequence,
    MoneyReceipt,
    Payment,
    PaymentAllocation,
    ReceiptSequence,
    Refund,
    StudentFeeAssignment,
    StudentWaiver,
    WaiverRule,
)


class FeeStructureItemInline(admin.TabularInline):
    model = FeeStructureItem
    extra = 1


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ["amount", "waiver_amount", "fine_amount", "payable_amount", "paid_amount"]


@admin.register(FeeHead)
class FeeHeadAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name_en",
        "name_bn",
        "fee_type",
        "recurrence",
        "is_optional",
        "is_active",
        "institution",
    ]
    list_filter = ["fee_type", "recurrence", "is_optional", "is_active", "institution"]
    search_fields = ["code", "name_en", "name_bn"]


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ["name", "class_level", "session", "is_active", "institution"]
    list_filter = ["session", "class_level", "is_active", "institution"]
    search_fields = ["name"]
    inlines = [FeeStructureItemInline]


@admin.register(StudentFeeAssignment)
class StudentFeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ["student", "fee_head", "custom_amount", "is_exempt", "institution"]
    list_filter = ["is_exempt", "fee_head", "institution"]
    search_fields = ["student__student_id", "student__name_en"]


@admin.register(WaiverRule)
class WaiverRuleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "discount_type",
        "discount_value",
        "is_active",
        "institution",
    ]
    list_filter = ["category", "discount_type", "is_active", "institution"]
    search_fields = ["name"]


@admin.register(StudentWaiver)
class StudentWaiverAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "title",
        "discount_type",
        "discount_value",
        "status",
        "approved_by",
        "institution",
    ]
    list_filter = ["status", "discount_type", "institution"]
    search_fields = ["student__student_id", "student__name_en", "title"]


@admin.register(FineRule)
class FineRuleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "fine_type",
        "grace_period_days",
        "amount",
        "max_fine_amount",
        "is_active",
        "institution",
    ]
    list_filter = ["fine_type", "is_active", "institution"]
    search_fields = ["name"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "student",
        "title",
        "subtotal_amount",
        "waiver_amount",
        "fine_amount",
        "total_payable",
        "paid_amount",
        "due_amount",
        "status",
        "due_date",
        "institution",
    ]
    list_filter = ["status", "invoice_type", "billing_year", "billing_month", "institution"]
    search_fields = ["invoice_number", "student__student_id", "student__name_en", "title"]
    inlines = [InvoiceLineInline]


@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ["institution", "year", "last_number"]
    list_filter = ["year", "institution"]


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    readonly_fields = ["invoice", "invoice_line", "allocated_amount"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_id",
        "student",
        "payment_method",
        "amount",
        "status",
        "payment_date",
        "institution",
    ]
    list_filter = ["payment_method", "status", "institution"]
    search_fields = [
        "transaction_id",
        "gateway_order_id",
        "student__student_id",
        "idempotency_key",
    ]
    inlines = [PaymentAllocationInline]


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ["payment", "invoice", "invoice_line", "allocated_amount"]
    search_fields = ["payment__transaction_id", "invoice__invoice_number"]


@admin.register(MoneyReceipt)
class MoneyReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "receipt_number",
        "payment",
        "student",
        "total_amount",
        "issued_at",
        "is_cancelled",
        "institution",
    ]
    list_filter = ["is_cancelled", "institution"]
    search_fields = ["receipt_number", "student__student_id"]


@admin.register(ReceiptSequence)
class ReceiptSequenceAdmin(admin.ModelAdmin):
    list_display = ["institution", "year", "last_number"]
    list_filter = ["year", "institution"]


class AdvanceTransactionInline(admin.TabularInline):
    model = AdvanceTransaction
    extra = 0
    readonly_fields = [
        "transaction_type",
        "amount",
        "balance_after",
        "invoice",
        "description",
        "created_at",
    ]


@admin.register(AdvanceBalance)
class AdvanceBalanceAdmin(admin.ModelAdmin):
    list_display = ["student", "current_balance", "institution"]
    search_fields = ["student__student_id", "student__name_en"]
    inlines = [AdvanceTransactionInline]


@admin.register(AdvanceTransaction)
class AdvanceTransactionAdmin(admin.ModelAdmin):
    list_display = ["advance_balance", "transaction_type", "amount", "balance_after", "created_at"]
    list_filter = ["transaction_type"]
    search_fields = ["advance_balance__student__student_id", "description"]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        "payment",
        "student",
        "amount",
        "status",
        "requested_by",
        "approved_by",
        "created_at",
        "institution",
    ]
    list_filter = ["status", "institution"]
    search_fields = ["payment__transaction_id", "student__student_id", "reason"]
