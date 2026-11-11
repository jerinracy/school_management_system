"""Django Admin configuration for Staff and HR module."""

from django.contrib import admin

from apps.staff.models import (
    Department,
    Designation,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Staff,
    StaffDocument,
    StaffEducation,
    StaffIDCard,
    TeacherAssignment,
)


class StaffEducationInline(admin.TabularInline):
    model = StaffEducation
    extra = 0


class StaffDocumentInline(admin.TabularInline):
    model = StaffDocument
    extra = 0


class StaffIDCardInline(admin.TabularInline):
    model = StaffIDCard
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "head_of_department", "institution"]
    search_fields = ["name", "code"]
    list_filter = ["institution"]


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ["title", "title_bn", "rank_order", "role_category", "institution"]
    list_filter = ["role_category", "institution"]
    search_fields = ["title", "title_bn", "code"]


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id",
        "full_name_en",
        "designation",
        "department",
        "staff_type",
        "phone",
        "status",
        "is_mpo",
        "joining_date",
    ]
    list_filter = ["staff_type", "status", "is_mpo", "department", "designation", "institution"]
    search_fields = [
        "employee_id",
        "full_name_en",
        "full_name_bn",
        "phone",
        "nid",
        "mpo_index_number",
    ]
    inlines = [StaffEducationInline, StaffDocumentInline, StaffIDCardInline]
    raw_id_fields = ["user", "department", "designation"]


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "yearly_quota",
        "is_paid",
        "allow_carry_forward",
        "gender_restriction",
    ]
    search_fields = ["name", "code"]
    list_filter = ["is_paid", "allow_carry_forward", "gender_restriction", "institution"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ["staff", "leave_type", "session", "allocated_days", "used_days", "pending_days"]
    search_fields = ["staff__full_name_en", "staff__employee_id"]
    list_filter = ["leave_type", "session", "institution"]
    raw_id_fields = ["staff"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "staff",
        "leave_type",
        "session",
        "start_date",
        "end_date",
        "days_count",
        "status",
    ]
    search_fields = ["staff__full_name_en", "staff__employee_id"]
    list_filter = ["status", "leave_type", "session", "institution"]
    raw_id_fields = ["staff", "recommender", "approver"]


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "teacher",
        "subject",
        "section",
        "session",
        "periods_per_week",
        "is_primary_teacher",
    ]
    search_fields = ["teacher__full_name_en", "teacher__employee_id", "subject__name_en"]
    list_filter = ["session", "is_primary_teacher", "institution"]
    raw_id_fields = ["teacher", "subject", "section"]
