"""Django admin registration for devices, punches, enrollments, and commands."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.devices.models import (
    BiometricConsent,
    BiometricEnrollment,
    Device,
    DeviceCommand,
    DeviceGroup,
    DeviceGroupMember,
    DeviceHealthLog,
    DeviceUserMap,
    RawPunch,
)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "vendor",
        "model",
        "serial_no",
        "protocol",
        "status",
        "branch",
        "last_seen",
        "is_active",
    ]
    list_filter = ["status", "protocol", "device_type", "vendor", "is_active", "institution"]
    search_fields = ["name", "serial_no", "model", "location"]
    readonly_fields = ["id", "created_at", "updated_at", "last_seen"]


class DeviceGroupMemberInline(admin.TabularInline):
    model = DeviceGroupMember
    extra = 1


@admin.register(DeviceGroup)
class DeviceGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "target_audience", "institution", "created_at"]
    list_filter = ["target_audience", "institution"]
    search_fields = ["name", "description"]
    inlines = [DeviceGroupMemberInline]


@admin.register(DeviceUserMap)
class DeviceUserMapAdmin(admin.ModelAdmin):
    list_display = ["device", "device_user_id", "user_type", "student", "staff", "rfid_card"]
    list_filter = ["user_type", "device__institution", "device"]
    search_fields = ["device_user_id", "rfid_card", "student__name_en", "staff__full_name_en"]


@admin.register(BiometricConsent)
class BiometricConsentAdmin(admin.ModelAdmin):
    list_display = [
        "subject_type",
        "student",
        "staff",
        "guardian",
        "granted_at",
        "withdrawn_at",
        "is_active",
    ]
    list_filter = ["subject_type", "consent_version", "institution"]
    search_fields = ["student__name_en", "staff__full_name_en", "guardian__name_en"]
    readonly_fields = ["granted_at"]


@admin.register(BiometricEnrollment)
class BiometricEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "subject_type",
        "student",
        "staff",
        "device",
        "method",
        "device_user_id",
        "is_active",
        "enrolled_at",
    ]
    list_filter = ["method", "subject_type", "is_active", "device"]
    search_fields = ["device_user_id", "student__name_en", "staff__full_name_en"]
    readonly_fields = ["enrolled_at"]


@admin.register(DeviceCommand)
class DeviceCommandAdmin(admin.ModelAdmin):
    list_display = ["device", "command_type", "status", "sent_at", "acknowledged_at", "created_at"]
    list_filter = ["status", "command_type", "device"]
    search_fields = ["payload", "response_message"]
    readonly_fields = ["sent_at", "acknowledged_at", "created_at"]


@admin.register(DeviceHealthLog)
class DeviceHealthLogAdmin(admin.ModelAdmin):
    list_display = ["device", "device_time", "server_time", "clock_drift_seconds", "status_ok"]
    list_filter = ["status_ok", "device"]
    readonly_fields = ["server_time", "created_at"]


@admin.register(RawPunch)
class RawPunchAdmin(admin.ModelAdmin):
    list_display = [
        "device",
        "raw_user_id",
        "device_time",
        "received_at",
        "status",
        "resolved_student",
        "resolved_staff",
    ]
    list_filter = ["status", "verify_type", "punch_state", "device"]
    search_fields = ["raw_user_id", "serial_no"]
    readonly_fields = [
        "id",
        "device",
        "serial_no",
        "raw_user_id",
        "device_time",
        "received_at",
        "clock_drift_seconds",
        "verify_type",
        "punch_state",
        "work_code",
        "payload_hash",
        "status",
        "resolved_student",
        "resolved_staff",
        "error_message",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        # Raw punch is append-only from devices; forbid manual creation in admin
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        # Raw punch is immutable audit log; forbid deletion
        return False
