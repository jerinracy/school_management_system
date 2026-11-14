"""Serializers for Student Management."""

from decimal import Decimal
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from apps.core.utils.phone import normalize_bd_phone
from apps.students.models import (
    EnrollmentStatus,
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
from apps.students.services.intake import generate_next_student_id


class StudentEnrollmentBriefSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="class_level.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    shift_name = serializers.CharField(source="shift.name", read_only=True, default=None)

    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student",
            "session",
            "session_name",
            "class_level",
            "class_name",
            "section",
            "section_name",
            "group",
            "group_name",
            "shift",
            "shift_name",
            "roll_no",
            "enrollment_date",
            "status",
        ]


class StudentEnrollmentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student",
            "session",
            "class_level",
            "section",
            "group",
            "shift",
            "roll_no",
            "enrollment_date",
            "status",
        ]
        extra_kwargs = {
            "enrollment_date": {"required": False},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        from django.utils import timezone

        if not attrs.get("enrollment_date"):
            attrs["enrollment_date"] = timezone.localdate()

        section = attrs.get("section")
        class_level = attrs.get("class_level")
        if section and class_level and section.class_level_id != class_level.id:
            raise serializers.ValidationError(
                {
                    "section": f"Section '{section.name}' does not belong to class '{class_level.name}'."
                }
            )

        return attrs


class StudentListSerializer(serializers.ModelSerializer):
    active_enrollment = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name_en",
            "name_bn",
            "gender",
            "blood_group",
            "religion",
            "status",
            "admission_date",
            "active_enrollment",
        ]

    def get_active_enrollment(self, obj: Student) -> dict[str, Any] | None:
        enrollment = (
            obj.enrollments.filter(status=EnrollmentStatus.ACTIVE, is_deleted=False)
            .select_related("class_level", "section", "session")
            .first()
        )
        if not enrollment:
            return None
        return StudentEnrollmentBriefSerializer(enrollment).data


class PreviousSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreviousSchool
        fields = [
            "id",
            "school_name",
            "board",
            "last_class_passed",
            "tc_number",
            "tc_date",
            "gpa_obtained",
        ]


class StudentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDocument
        fields = [
            "id",
            "document_type",
            "title",
            "file",
            "is_verified",
            "verified_at",
            "verified_by",
            "created_at",
        ]
        read_only_fields = ["is_verified", "verified_at", "verified_by", "created_at"]


class StudentIDCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentIDCard
        fields = [
            "id",
            "card_no",
            "qr_payload",
            "rfid_uid",
            "issue_date",
            "expiry_date",
            "is_active",
            "printed_at",
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    enrollments = StudentEnrollmentBriefSerializer(many=True, read_only=True)
    previous_school = PreviousSchoolSerializer(read_only=True)
    documents = StudentDocumentSerializer(many=True, read_only=True)
    id_cards = StudentIDCardSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name_en",
            "name_bn",
            "dob",
            "gender",
            "blood_group",
            "religion",
            "birth_reg_no",
            "photo",
            "present_address",
            "permanent_address",
            "status",
            "admission_date",
            "is_orphan",
            "has_disability",
            "disability_details",
            "quota_category",
            "has_stipend",
            "emergency_contact_name",
            "emergency_contact_phone",
            "enrollments",
            "previous_school",
            "documents",
            "id_cards",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance: Student) -> dict[str, Any]:
        data = super().to_representation(instance)
        request = self.context.get("request")
        # Mask sensitive birth_reg_no and phone if user is not staff/admin
        if request and request.user and not (request.user.is_staff or request.user.is_superuser):
            if not request.user.has_perm("students.manage"):
                if data.get("birth_reg_no") and len(data["birth_reg_no"]) == 17:
                    data["birth_reg_no"] = (
                        data["birth_reg_no"][:4] + "*********" + data["birth_reg_no"][-4:]
                    )
                if (
                    data.get("emergency_contact_phone")
                    and len(data["emergency_contact_phone"]) >= 10
                ):
                    data["emergency_contact_phone"] = (
                        data["emergency_contact_phone"][:4]
                        + "****"
                        + data["emergency_contact_phone"][-3:]
                    )
        return data


class StudentCreateUpdateSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(max_length=32, required=False)

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name_en",
            "name_bn",
            "dob",
            "gender",
            "blood_group",
            "religion",
            "birth_reg_no",
            "photo",
            "present_address",
            "permanent_address",
            "status",
            "admission_date",
            "is_orphan",
            "has_disability",
            "disability_details",
            "quota_category",
            "has_stipend",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data: dict[str, Any]) -> Student:
        if not validated_data.get("student_id"):
            institution = validated_data.get("institution")
            current_year = str(timezone.localdate().year)
            if institution:
                validated_data["student_id"] = generate_next_student_id(
                    institution_id=institution.id,
                    session_year=current_year,
                    class_order=1,
                )
            else:
                validated_data["student_id"] = f"{current_year}010001"
        return super().create(validated_data)

    def validate_birth_reg_no(self, value: str | None) -> str | None:
        if value:
            cleaned = value.strip()
            if len(cleaned) != 17 or not cleaned.isdigit():
                raise serializers.ValidationError(
                    "Bangladeshi Birth Registration Number must be exactly 17 digits."
                )
            return cleaned
        return value

    def validate_emergency_contact_phone(self, value: str | None) -> str:
        if value:
            return normalize_bd_phone(value)
        return ""


class AdmitFromApplicationSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    roll_no = serializers.IntegerField(min_value=1)
    session_id = serializers.UUIDField(required=False)
    student_id = serializers.CharField(max_length=32, required=False)


class AutoAssignRollsSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    strategy = serializers.ChoiceField(
        choices=["name_en", "name_bn", "student_id"], default="name_en"
    )


class PromotionItemSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_id_str = serializers.CharField(source="student.student_id", read_only=True)
    target_class_name = serializers.CharField(source="target_class.name", read_only=True)
    target_section_name = serializers.CharField(source="target_section.name", read_only=True)

    class Meta:
        model = PromotionItem
        fields = [
            "id",
            "student",
            "student_id_str",
            "student_name",
            "from_enrollment",
            "target_class",
            "target_class_name",
            "target_section",
            "target_section_name",
            "target_roll_no",
            "action",
            "gpa",
            "remarks",
        ]


class PromotionBatchSerializer(serializers.ModelSerializer):
    from_session_name = serializers.CharField(source="from_session.name", read_only=True)
    to_session_name = serializers.CharField(source="to_session.name", read_only=True)
    from_class_name = serializers.CharField(source="from_class.name", read_only=True)
    to_class_name = serializers.CharField(source="to_class.name", read_only=True)
    items = PromotionItemSerializer(many=True, read_only=True)

    class Meta:
        model = PromotionBatch
        fields = [
            "id",
            "from_session",
            "from_session_name",
            "to_session",
            "to_session_name",
            "from_class",
            "from_class_name",
            "to_class",
            "to_class_name",
            "status",
            "total_students",
            "promoted_count",
            "retained_count",
            "applied_at",
            "created_at",
            "items",
        ]


class PromotionPreviewRequestSerializer(serializers.Serializer):
    from_session_id = serializers.UUIDField()
    to_session_id = serializers.UUIDField()
    from_class_id = serializers.UUIDField()
    to_class_id = serializers.UUIDField()
    default_target_section_id = serializers.UUIDField(required=False)
    passing_gpa_threshold = serializers.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("2.00")
    )
    student_overrides = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )


class TransferCertificateSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True)
    student_id_str = serializers.CharField(source="student.student_id", read_only=True)

    class Meta:
        model = TransferCertificate
        fields = [
            "id",
            "student",
            "student_id_str",
            "student_name_en",
            "student_name_bn",
            "enrollment",
            "tc_number",
            "issue_date",
            "reason",
            "conduct_remarks",
            "dues_cleared",
            "pdf_file",
            "created_at",
        ]
        read_only_fields = ["tc_number", "pdf_file", "created_at"]


class IssueTCSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    reason = serializers.CharField()
    conduct_remarks = serializers.CharField(default="Satisfactory")
    dues_cleared = serializers.BooleanField(default=True)


class TestimonialSerializer(serializers.ModelSerializer):
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_id_str = serializers.CharField(source="student.student_id", read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            "id",
            "student",
            "student_id_str",
            "student_name_en",
            "enrollment",
            "certificate_no",
            "issue_date",
            "exam_name",
            "passing_year",
            "gpa",
            "character",
            "pdf_file",
            "created_at",
        ]
        read_only_fields = ["certificate_no", "pdf_file", "created_at"]


class IssueTestimonialSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    exam_name = serializers.CharField()
    passing_year = serializers.IntegerField(min_value=2000, max_value=2100)
    gpa = serializers.DecimalField(max_digits=4, decimal_places=2)
    character = serializers.CharField(default="Good")


class BulkImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    dry_run = serializers.BooleanField(default=True)
