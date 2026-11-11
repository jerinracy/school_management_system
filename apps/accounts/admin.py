"""Django admin configuration for accounts models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginAttempt, OTPChallenge, Role, User, UserRole, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "phone",
        "email",
        "full_name",
        "user_type",
        "institution",
        "is_active",
        "is_staff",
    )
    list_filter = ("user_type", "is_active", "is_staff", "institution")
    search_fields = ("username", "phone", "email", "full_name")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("full_name", "email", "phone", "avatar", "language_preference")},
        ),
        ("Tenant info", {"fields": ("institution", "user_type", "must_change_password")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "is_system", "created_at")
    list_filter = ("is_system", "institution")
    search_fields = ("name", "code", "institution__name_en")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "branch", "created_at")
    list_filter = ("role", "branch")
    search_fields = ("user__username", "role__name")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "ip_address", "last_seen_at", "revoked_at")
    list_filter = ("platform",)
    search_fields = ("user__username", "device_id", "ip_address")


@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ("phone", "purpose", "expires_at", "attempts", "used_at", "created_at")
    list_filter = ("purpose",)
    search_fields = ("phone",)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("identifier", "ip_address", "successful", "created_at")
    list_filter = ("successful",)
    search_fields = ("identifier", "ip_address")
