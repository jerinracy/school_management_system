"""Django admin registration for attendance policies, daily records, and logs."""

from django.contrib import admin

from apps.attendance.models import (
    AttendanceCorrection,
    AttendanceEvent,
    AttendancePolicy,
    DailyAttendance,
    MobileCheckin,
    PeriodAttendance,
    PolicyAssignment,
)


@admin.register(AttendancePolicy)
class AttendancePolicyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "user_type",
        "start_time",
        "end_time",
        "grace_minutes",
        "late_threshold_minutes",
        "multi_punch_mode",
        "version",
        "is_active",
        "institution",
    ]
    list_filter = ["user_type", "multi_punch_mode", "is_active", "institution"]
    search_fields = ["name"]


@admin.register(PolicyAssignment)
class PolicyAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "policy",
        "user_type",
        "priority",
        "branch",
        "shift",
        "class_level",
        "institution",
    ]
    list_filter = ["user_type", "institution"]


@admin.register(DailyAttendance)
class DailyAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "user_type",
        "student",
        "staff",
        "status",
        "first_in",
        "last_out",
        "total_minutes",
        "minutes_late",
        "is_overridden",
        "institution",
    ]
    list_filter = ["status", "user_type", "is_overridden", "date", "institution"]
    search_fields = [
        "student__name_en",
        "student__student_id",
        "staff__full_name_en",
        "staff__employee_id",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PeriodAttendance)
class PeriodAttendanceAdmin(admin.ModelAdmin):
    list_display = ["date", "section", "subject", "student", "teacher", "status", "institution"]
    list_filter = ["status", "date", "institution"]
    search_fields = ["student__name_en", "section__name", "subject__name_en"]


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = [
        "daily_attendance",
        "requested_by",
        "status_before",
        "status_after",
        "approval_status",
        "approved_by",
        "created_at",
    ]
    list_filter = ["approval_status", "institution"]
    search_fields = ["reason", "rejection_reason"]


@admin.register(AttendanceEvent)
class AttendanceEventAdmin(admin.ModelAdmin):
    list_display = [
        "user_type",
        "student",
        "staff",
        "direction",
        "method",
        "source",
        "timestamp",
        "is_processed",
        "institution",
    ]
    list_filter = ["source", "direction", "method", "user_type", "is_processed", "institution"]
    readonly_fields = [
        "user_type",
        "student",
        "staff",
        "direction",
        "method",
        "device",
        "timestamp",
        "source",
        "raw_punch",
        "is_processed",
        "created_at",
    ]


@admin.register(MobileCheckin)
class MobileCheckinAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "staff",
        "latitude",
        "longitude",
        "is_within_geofence",
        "geofence_distance_meters",
        "timestamp",
        "institution",
    ]
    list_filter = ["is_within_geofence", "institution"]
    readonly_fields = [
        "user",
        "staff",
        "latitude",
        "longitude",
        "accuracy_meters",
        "is_within_geofence",
        "geofence_distance_meters",
        "selfie_image",
        "device_info",
        "timestamp",
        "attendance_event",
        "created_at",
    ]
