"""Django admin configurations for Fee Management."""

from django.contrib import admin

from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FineRule,
    Invoice,
    InvoiceLine,
    InvoiceSequence,
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
