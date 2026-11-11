"""Django admin registration for examination models."""

from django.contrib import admin

from apps.exams.models import (
    AdmitCard,
    Exam,
    ExamEligibilityPolicy,
    ExamRoutine,
    ExamSubject,
    ExamType,
    GraceMarkRule,
    MarkEntry,
    MarkEntryLog,
    ReScrutinyRequest,
    SeatPlan,
    StudentExamEligibility,
)


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_board_exam", "institution"]
    search_fields = ["name", "code"]
    list_filter = ["is_board_exam"]


class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 0
    fields = [
        "class_level",
        "subject",
        "exam_date",
        "full_marks",
        "creative_full_marks",
        "mcq_full_marks",
        "is_marks_locked",
    ]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "exam_type",
        "session",
        "start_date",
        "end_date",
        "status",
        "is_active",
        "institution",
    ]
    list_filter = ["status", "is_active", "session", "exam_type"]
    search_fields = ["name", "term"]
    inlines = [ExamSubjectInline]


@admin.register(ExamSubject)
class ExamSubjectAdmin(admin.ModelAdmin):
    list_display = [
        "exam",
        "class_level",
        "subject",
        "exam_date",
        "full_marks",
        "pass_marks",
        "assigned_teacher",
        "is_marks_locked",
    ]
    list_filter = ["exam", "class_level", "is_marks_locked"]
    search_fields = ["subject__name_en", "class_level__name"]


@admin.register(ExamRoutine)
class ExamRoutineAdmin(admin.ModelAdmin):
    list_display = ["exam", "exam_subject", "exam_date", "start_time", "end_time", "room_number"]
    list_filter = ["exam", "exam_date"]


@admin.register(ExamEligibilityPolicy)
class ExamEligibilityPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "exam",
        "min_attendance_percentage",
        "non_collegiate_threshold",
        "allow_non_collegiate",
        "require_fee_clearance",
        "institution",
    ]


@admin.register(StudentExamEligibility)
class StudentExamEligibilityAdmin(admin.ModelAdmin):
    list_display = ["student", "exam", "attendance_percentage", "dues_cleared", "clearance_status"]
    list_filter = ["clearance_status", "dues_cleared", "exam"]
    search_fields = ["student__name_en", "student__student_id"]


@admin.register(SeatPlan)
class SeatPlanAdmin(admin.ModelAdmin):
    list_display = ["exam", "room_number", "bench_label", "seat_number", "roll_number", "student"]
    list_filter = ["exam", "room_number", "class_level"]
    search_fields = ["student__name_en", "student__student_id", "room_number"]


@admin.register(AdmitCard)
class AdmitCardAdmin(admin.ModelAdmin):
    list_display = ["card_number", "student", "exam", "issue_date", "is_issued"]
    list_filter = ["is_issued", "exam"]
    search_fields = ["card_number", "student__name_en", "student__student_id"]


class MarkEntryLogInLine(admin.TabularInline):
    model = MarkEntryLog
    extra = 0
    readonly_fields = ["modified_by", "field_name", "old_value", "new_value", "reason", "timestamp"]


@admin.register(MarkEntry)
class MarkEntryAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "exam_subject",
        "creative_marks",
        "mcq_marks",
        "practical_marks",
        "total_marks",
        "is_absent",
        "is_locked",
    ]
    list_filter = ["is_absent", "is_locked", "exam_subject__exam"]
    search_fields = ["student__name_en", "student__student_id"]
    inlines = [MarkEntryLogInLine]


@admin.register(MarkEntryLog)
class MarkEntryLogAdmin(admin.ModelAdmin):
    list_display = [
        "mark_entry",
        "field_name",
        "old_value",
        "new_value",
        "modified_by",
        "timestamp",
    ]
    search_fields = ["mark_entry__student__student_id", "field_name"]


@admin.register(ReScrutinyRequest)
class ReScrutinyRequestAdmin(admin.ModelAdmin):
    list_display = ["student", "exam_subject", "status", "fee_paid", "created_at"]
    list_filter = ["status", "fee_paid"]
    search_fields = ["student__name_en", "student__student_id"]


@admin.register(GraceMarkRule)
class GraceMarkRuleAdmin(admin.ModelAdmin):
    list_display = ["exam", "subject", "max_grace_marks", "is_active"]
    list_filter = ["is_active", "exam"]
