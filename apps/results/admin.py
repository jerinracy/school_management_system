"""Django admin configuration for Results and Grading Engine models."""

from django.contrib import admin

from apps.results.models import (
    CombinedSubjectResult,
    CumulativeResult,
    ExamResult,
    GradeTier,
    GradingScale,
    StudentOptionalSubject,
    SubjectResult,
    TermWeightageRule,
)


class GradeTierInline(admin.TabularInline):
    model = GradeTier
    extra = 0
    fields = [
        "letter_grade",
        "grade_point",
        "min_percentage",
        "max_percentage",
        "remarks_en",
        "remarks_bn",
    ]


@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):
    list_display = ["name", "scale_type", "max_gpa", "pass_gpa", "is_default", "institution"]
    list_filter = ["scale_type", "is_default", "institution"]
    search_fields = ["name", "description"]
    inlines = [GradeTierInline]


@admin.register(GradeTier)
class GradeTierAdmin(admin.ModelAdmin):
    list_display = [
        "letter_grade",
        "grade_point",
        "min_percentage",
        "max_percentage",
        "scale",
        "institution",
    ]
    list_filter = ["scale", "institution"]
    search_fields = ["letter_grade", "remarks_en", "remarks_bn"]


@admin.register(StudentOptionalSubject)
class StudentOptionalSubjectAdmin(admin.ModelAdmin):
    list_display = ["student", "subject", "session", "class_level", "institution"]
    list_filter = ["session", "class_level", "institution"]
    search_fields = ["student__name_en", "student__student_id", "subject__name_en"]


@admin.register(SubjectResult)
class SubjectResultAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "exam_subject",
        "total_marks",
        "marks_percentage",
        "grade_point",
        "letter_grade",
        "is_passed",
        "is_absent",
        "is_fourth_subject",
        "institution",
    ]
    list_filter = ["is_passed", "is_absent", "is_fourth_subject", "letter_grade", "exam"]
    search_fields = ["student__name_en", "student__student_id", "exam_subject__subject__name_en"]


@admin.register(CombinedSubjectResult)
class CombinedSubjectResultAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "combined_name",
        "total_marks",
        "grade_point",
        "letter_grade",
        "is_passed",
        "exam",
    ]
    list_filter = ["is_passed", "letter_grade", "exam"]
    search_fields = ["student__name_en", "student__student_id", "combined_name"]


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "exam",
        "final_gpa",
        "final_grade",
        "total_marks",
        "is_passed",
        "class_position",
        "section_position",
        "status",
    ]
    list_filter = ["status", "is_passed", "final_grade", "exam"]
    search_fields = ["student__name_en", "student__student_id"]


@admin.register(TermWeightageRule)
class TermWeightageRuleAdmin(admin.ModelAdmin):
    list_display = ["class_level", "exam", "session", "weightage_percentage", "institution"]
    list_filter = ["session", "class_level"]


@admin.register(CumulativeResult)
class CumulativeResultAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "class_level",
        "session",
        "cumulative_gpa",
        "cumulative_grade",
        "is_passed",
        "final_class_position",
        "promotion_recommended",
    ]
    list_filter = ["is_passed", "promotion_recommended", "session", "class_level"]
    search_fields = ["student__name_en", "student__student_id"]
