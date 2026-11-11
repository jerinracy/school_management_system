"""Admin registration for academic models."""

from django.contrib import admin

from apps.academics.models import (
    ClassLevel,
    ClassSubject,
    Group,
    Period,
    Room,
    RoutineSlot,
    Section,
    Subject,
    SubstituteAssignment,
)


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "medium", "order", "has_groups", "institution"]
    list_filter = ["medium", "has_groups", "institution"]
    search_fields = ["name", "code"]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "institution"]
    search_fields = ["name", "code"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "class_level",
        "shift",
        "session",
        "capacity",
        "teacher_user",
        "institution",
    ]
    list_filter = ["class_level", "shift", "session", "institution"]
    search_fields = ["name", "class_level__name"]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["code", "name_en", "name_bn", "type", "has_papers", "institution"]
    list_filter = ["type", "has_papers", "institution"]
    search_fields = ["code", "name_en", "name_bn"]


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = [
        "class_level",
        "group",
        "subject",
        "session",
        "full_marks",
        "credit_weight",
        "is_optional_elective",
        "institution",
    ]
    list_filter = ["class_level", "group", "session", "is_optional_elective", "institution"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "branch", "type", "capacity", "institution"]
    list_filter = ["type", "branch", "institution"]
    search_fields = ["name"]


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ["name", "shift", "start_time", "end_time", "order", "is_break", "institution"]
    list_filter = ["shift", "is_break", "institution"]
    ordering = ["shift", "order"]


@admin.register(RoutineSlot)
class RoutineSlotAdmin(admin.ModelAdmin):
    list_display = [
        "section",
        "weekday",
        "period",
        "subject",
        "teacher_user",
        "room",
        "institution",
    ]
    list_filter = ["weekday", "section__class_level", "institution"]
    search_fields = ["section__name", "subject__name_en"]


@admin.register(SubstituteAssignment)
class SubstituteAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "slot_date",
        "routine_slot",
        "original_teacher",
        "substitute_teacher",
        "institution",
    ]
    list_filter = ["slot_date", "institution"]
    search_fields = ["substitute_teacher__full_name", "reason"]
