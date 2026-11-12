"""Django admin registrations for Homework & Learning Management."""

from django.contrib import admin

from apps.homework.models import (
    Homework,
    HomeworkAttachment,
    HomeworkSubmission,
    LessonPlan,
    OnlineClassLink,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    StudyMaterial,
    SubmissionAttachment,
    SyllabusTopic,
)


class HomeworkAttachmentInline(admin.TabularInline):
    model = HomeworkAttachment
    extra = 0


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ("title", "class_level", "section", "subject", "due_at", "status", "institution")
    list_filter = ("status", "class_level", "subject", "institution")
    search_fields = ("title", "description")
    inlines = [HomeworkAttachmentInline]


class SubmissionAttachmentInline(admin.TabularInline):
    model = SubmissionAttachment
    extra = 0


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ("homework", "student", "status", "is_late", "marks_obtained", "submitted_at")
    list_filter = ("status", "is_late", "institution")
    search_fields = ("student__student_id", "student__name_en", "homework__title")
    inlines = [SubmissionAttachmentInline]


@admin.register(SyllabusTopic)
class SyllabusTopicAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "class_level",
        "subject",
        "order",
        "status",
        "completion_percentage",
        "institution",
    )
    list_filter = ("status", "class_level", "subject", "institution")
    search_fields = ("title", "title_bn")


@admin.register(LessonPlan)
class LessonPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "class_level", "subject", "lesson_date", "status", "institution")
    list_filter = ("status", "class_level", "subject", "institution")
    search_fields = ("title", "objectives")


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "class_level",
        "subject",
        "material_type",
        "is_published",
        "institution",
    )
    list_filter = ("material_type", "is_published", "class_level", "institution")
    search_fields = ("title", "description")


@admin.register(OnlineClassLink)
class OnlineClassLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "class_level", "subject", "platform", "scheduled_start", "status")
    list_filter = ("platform", "status", "class_level", "institution")
    search_fields = ("title",)


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "class_level",
        "subject",
        "starts_at",
        "ends_at",
        "total_marks",
        "is_published",
    )
    list_filter = ("is_published", "class_level", "subject", "institution")
    search_fields = ("title",)
    inlines = [QuizQuestionInline]


admin.site.register(QuizOption)
admin.site.register(QuizAttempt)
