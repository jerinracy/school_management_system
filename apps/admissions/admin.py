"""Django Admin configuration for admission models."""

from django.contrib import admin

from apps.admissions.models import (
    AdmissionCircular,
    AdmissionTest,
    AdmissionTestResult,
    Application,
    ApplicationDocument,
    ApplicationPayment,
    LotteryDraw,
    MeritList,
    MeritListEntry,
    QuotaRule,
)


@admin.register(AdmissionCircular)
class AdmissionCircularAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "session",
        "class_level",
        "seats_available",
        "application_fee",
        "status",
        "institution",
    ]
    list_filter = ["status", "session", "class_level", "institution"]
    search_fields = ["title"]


@admin.register(QuotaRule)
class QuotaRuleAdmin(admin.ModelAdmin):
    list_display = [
        "circular",
        "name",
        "quota_type",
        "reserved_percentage",
        "reserved_seats",
        "priority",
        "institution",
    ]
    list_filter = ["quota_type", "circular", "institution"]


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0


class ApplicationPaymentInline(admin.TabularInline):
    model = ApplicationPayment
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "application_no",
        "name_en",
        "circular",
        "guardian_name",
        "guardian_phone",
        "status",
        "created_at",
        "institution",
    ]
    list_filter = ["status", "quota_type", "gender", "circular", "institution"]
    search_fields = ["application_no", "name_en", "name_bn", "guardian_phone", "birth_reg_no"]
    inlines = [ApplicationDocumentInline, ApplicationPaymentInline]


@admin.register(AdmissionTest)
class AdmissionTestAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "circular",
        "test_date",
        "venue",
        "total_marks",
        "pass_marks",
        "institution",
    ]
    list_filter = ["circular", "institution"]
    search_fields = ["title", "venue"]


@admin.register(AdmissionTestResult)
class AdmissionTestResultAdmin(admin.ModelAdmin):
    list_display = ["test", "application", "marks_obtained", "is_passed", "institution"]
    list_filter = ["is_passed", "test", "institution"]
    search_fields = ["application__application_no", "application__name_en"]


@admin.register(LotteryDraw)
class LotteryDrawAdmin(admin.ModelAdmin):
    list_display = [
        "circular",
        "seed",
        "draw_date",
        "total_candidates",
        "selected_candidates_count",
        "is_confirmed",
        "institution",
    ]
    list_filter = ["is_confirmed", "circular", "institution"]


class MeritListEntryInline(admin.TabularInline):
    model = MeritListEntry
    extra = 0


@admin.register(MeritList)
class MeritListAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "circular",
        "selection_criteria",
        "is_published",
        "published_at",
        "created_at",
        "institution",
    ]
    list_filter = ["selection_criteria", "is_published", "circular", "institution"]
    search_fields = ["title"]
    inlines = [MeritListEntryInline]
