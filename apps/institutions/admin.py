"""Django admin registration for institutions models."""

from django.contrib import admin

from .models import AcademicSession, Branch, Holiday, Institution, Shift, Term


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_bn", "eiin", "board", "type", "is_active", "created_at")
    list_filter = ("board", "type", "mpo_status", "is_active")
    search_fields = ("name_en", "name_bn", "eiin", "phone", "email")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "is_main", "created_at")
    list_filter = ("is_main", "institution")
    search_fields = ("name", "code", "institution__name_en")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("branch", "name", "start_time", "end_time", "institution")
    list_filter = ("name", "branch")
    search_fields = ("branch__name", "branch__code")


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "start_date", "end_date", "is_current", "status")
    list_filter = ("is_current", "status", "institution")
    search_fields = ("name", "institution__name_en")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "session", "order", "start_date", "end_date")
    list_filter = ("session__institution", "session")
    search_fields = ("name", "session__name")


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "start_date",
        "end_date",
        "applies_to_all_branches",
        "institution",
    )
    list_filter = ("type", "applies_to_all_branches", "institution")
    search_fields = ("name", "description")
