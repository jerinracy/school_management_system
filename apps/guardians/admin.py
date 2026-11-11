"""Django Admin configuration for Guardians and Family module."""

from django.contrib import admin

from apps.guardians.models import AuthorizedPickup, Family, Guardian, StudentGuardian


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    extra = 0
    raw_id_fields = ["student"]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = [
        "name_en",
        "phone",
        "relation_default",
        "family",
        "is_emergency_contact",
        "created_at",
    ]
    list_filter = ["relation_default", "is_emergency_contact", "institution"]
    search_fields = ["name_en", "name_bn", "phone", "nid"]
    inlines = [StudentGuardianInline]
    raw_id_fields = ["user", "family"]


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = [
        "guardian",
        "student",
        "relation",
        "is_primary",
        "can_pickup",
        "receives_sms",
        "financial_responsible",
    ]
    list_filter = ["relation", "is_primary", "can_pickup", "receives_sms", "institution"]
    search_fields = [
        "guardian__name_en",
        "guardian__phone",
        "student__name_en",
        "student__student_id",
    ]
    raw_id_fields = ["guardian", "student"]


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ["family_code", "name", "primary_contact_phone", "created_at"]
    search_fields = ["family_code", "name", "primary_contact_phone"]
    list_filter = ["institution"]


@admin.register(AuthorizedPickup)
class AuthorizedPickupAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "student",
        "relation",
        "phone",
        "is_active",
        "otp_verified",
        "created_at",
    ]
    list_filter = ["is_active", "otp_verified", "institution"]
    search_fields = ["name", "phone", "nid", "student__name_en"]
    raw_id_fields = ["student"]
