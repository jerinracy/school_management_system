"""Django Admin registrations for Hostel Management."""

from django.contrib import admin

from apps.hostel.models import (
    Bed,
    GatePass,
    Hostel,
    HostelAllocation,
    HostelAttendance,
    HostelFeeLink,
    HostelVisitorLog,
    MealAttendance,
    MealPlan,
    Room,
)


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "hostel_type", "curfew_time", "is_active")
    list_filter = ("hostel_type", "is_active")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("hostel", "room_number", "floor", "capacity", "monthly_fee")


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("room", "bed_number", "status")
    list_filter = ("status",)


@admin.register(HostelFeeLink)
class HostelFeeLinkAdmin(admin.ModelAdmin):
    list_display = ("hostel", "session", "fee_head", "effective_amount")


@admin.register(HostelAllocation)
class HostelAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "hostel",
        "room",
        "bed",
        "allocated_date",
        "vacated_date",
        "is_active",
    )
    list_filter = ("is_active",)


@admin.register(HostelAttendance)
class HostelAttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "hostel", "attendance_date", "event_type", "status")
    list_filter = ("event_type", "status")


@admin.register(GatePass)
class GatePassAdmin(admin.ModelAdmin):
    list_display = ("student", "hostel", "expected_out_at", "expected_return_at", "status")
    list_filter = ("status", "curfew_alert_sent")


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("hostel", "name", "meal_type", "unit_cost", "is_active")


@admin.register(MealAttendance)
class MealAttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "meal_plan", "meal_date", "consumed")


@admin.register(HostelVisitorLog)
class HostelVisitorLogAdmin(admin.ModelAdmin):
    list_display = ("visitor_name", "student", "hostel", "check_in_at", "check_out_at")
