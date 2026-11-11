"""Django admin registrations for Student models."""

from django.contrib import admin

from apps.students.models import (
    AlumniProfile,
    DropoutRecord,
    PreviousSchool,
    PromotionBatch,
    PromotionItem,
    Student,
    StudentDocument,
    StudentEnrollment,
    StudentIDCard,
    Testimonial,
    TransferCertificate,
)


class StudentEnrollmentInline(admin.TabularInline):
    model = StudentEnrollment
    extra = 0
    fields = ["session", "class_level", "section", "roll_no", "status", "enrollment_date"]


class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 0
    fields = ["document_type", "title", "file", "is_verified"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        "student_id",
        "name_en",
        "name_bn",
        "gender",
        "status",
        "admission_date",
        "institution",
    ]
    list_filter = ["status", "gender", "religion", "blood_group", "institution"]
    search_fields = ["student_id", "name_en", "name_bn", "birth_reg_no"]
    inlines = [StudentEnrollmentInline, StudentDocumentInline]


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "session",
        "class_level",
        "section",
        "roll_no",
        "status",
        "institution",
    ]
    list_filter = ["session", "class_level", "status", "institution"]
    search_fields = ["student__student_id", "student__name_en", "roll_no"]


@admin.register(StudentIDCard)
class StudentIDCardAdmin(admin.ModelAdmin):
    list_display = ["card_no", "student", "issue_date", "expiry_date", "is_active", "institution"]
    list_filter = ["is_active", "institution"]
    search_fields = ["card_no", "student__student_id", "student__name_en"]


@admin.register(PromotionBatch)
class PromotionBatchAdmin(admin.ModelAdmin):
    list_display = [
        "from_class",
        "to_class",
        "from_session",
        "to_session",
        "status",
        "total_students",
    ]
    list_filter = ["status", "institution"]


@admin.register(PromotionItem)
class PromotionItemAdmin(admin.ModelAdmin):
    list_display = [
        "batch",
        "student",
        "target_class",
        "target_section",
        "target_roll_no",
        "action",
    ]
    list_filter = ["action", "target_class"]


@admin.register(TransferCertificate)
class TransferCertificateAdmin(admin.ModelAdmin):
    list_display = ["tc_number", "student", "issue_date", "dues_cleared", "institution"]
    search_fields = ["tc_number", "student__student_id", "student__name_en"]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["certificate_no", "student", "exam_name", "passing_year", "gpa", "institution"]
    search_fields = ["certificate_no", "student__student_id", "student__name_en"]


admin.site.register(PreviousSchool)
admin.site.register(DropoutRecord)
admin.site.register(AlumniProfile)
