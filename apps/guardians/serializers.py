"""Serializers for Guardians, Families, and Authorized Pickups."""

from typing import Any

from rest_framework import serializers

from apps.core.utils.phone import normalize_bd_phone
from apps.guardians.models import (
    AuthorizedPickup,
    Family,
    Guardian,
    GuardianRelation,
    StudentGuardian,
)
from apps.students.models import Student


class FamilySerializer(serializers.ModelSerializer):
    """Serializer for Family households."""

    primary_contact_phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Family
        fields = [
            "id",
            "family_code",
            "name",
            "primary_contact_phone",
            "address",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "family_code", "created_at", "updated_at"]

    def validate_primary_contact_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value


class StudentGuardianSerializer(serializers.ModelSerializer):
    """Serializer for Student-Guardian relationship links."""

    student_name = serializers.CharField(source="student.name_en", read_only=True)
    guardian_name = serializers.CharField(source="guardian.name_en", read_only=True)
    guardian_phone = serializers.CharField(source="guardian.phone", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            "id",
            "student",
            "student_name",
            "guardian",
            "guardian_name",
            "guardian_phone",
            "relation",
            "is_primary",
            "can_pickup",
            "receives_sms",
            "financial_responsible",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class GuardianSerializer(serializers.ModelSerializer):
    """Standard serializer for Guardian profiles."""

    phone = serializers.CharField()
    alt_phone = serializers.CharField(required=False, allow_blank=True)
    has_portal_account = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = [
            "id",
            "user",
            "has_portal_account",
            "family",
            "name_en",
            "name_bn",
            "relation_default",
            "phone",
            "alt_phone",
            "email",
            "nid",
            "occupation",
            "annual_income",
            "present_address",
            "permanent_address",
            "photo",
            "is_emergency_contact",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "has_portal_account", "created_at", "updated_at"]

    def get_has_portal_account(self, obj: Guardian) -> bool:
        return obj.user_id is not None

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)

    def validate_alt_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value


class GuardianDetailSerializer(GuardianSerializer):
    """Detailed guardian serializer embedding linked students."""

    student_relations = StudentGuardianSerializer(many=True, read_only=True)

    class Meta(GuardianSerializer.Meta):
        fields = GuardianSerializer.Meta.fields + ["student_relations"]


class AuthorizedPickupSerializer(serializers.ModelSerializer):
    """Serializer for authorized pickup persons."""

    student_name = serializers.CharField(source="student.name_en", read_only=True)
    phone = serializers.CharField()

    class Meta:
        model = AuthorizedPickup
        fields = [
            "id",
            "student",
            "student_name",
            "name",
            "relation",
            "phone",
            "nid",
            "photo",
            "is_active",
            "otp_verified",
            "otp_verified_at",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "otp_verified", "otp_verified_at", "created_at"]

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)


class LinkStudentActionSerializer(serializers.Serializer):
    """Payload to establish a student-guardian relationship."""

    student_id = serializers.UUIDField()
    relation = serializers.ChoiceField(
        choices=GuardianRelation.choices, default=GuardianRelation.FATHER
    )
    is_primary = serializers.BooleanField(default=False)
    can_pickup = serializers.BooleanField(default=True)
    receives_sms = serializers.BooleanField(default=True)
    financial_responsible = serializers.BooleanField(default=False)


class UnlinkStudentActionSerializer(serializers.Serializer):
    """Payload to disassociate a student from a guardian."""

    student_id = serializers.UUIDField()


class MergeGuardianActionSerializer(serializers.Serializer):
    """Payload to merge duplicate guardian records."""

    primary_guardian_id = serializers.UUIDField()
    duplicate_guardian_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class LinkSiblingsFamilySerializer(serializers.Serializer):
    """Payload to link multiple students and their guardians to a Family."""

    student_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class VerifyPickupOTPActionSerializer(serializers.Serializer):
    """Payload to verify OTP for authorized pickup."""

    otp = serializers.CharField(max_length=6, min_length=6)


class MyChildEnrollmentSerializer(serializers.Serializer):
    """Nested snapshot of student's current enrollment for parent portal."""

    session_name = serializers.CharField()
    class_name = serializers.CharField()
    section_name = serializers.CharField()
    roll_no = serializers.IntegerField()


class MyChildrenSerializer(serializers.Serializer):
    """Aggregated child detail view for logged-in guardians."""

    id = serializers.UUIDField()
    student_id = serializers.CharField()
    name_en = serializers.CharField()
    name_bn = serializers.CharField()
    gender = serializers.CharField()
    blood_group = serializers.CharField()
    status = serializers.CharField()
    photo = serializers.FileField(allow_null=True)
    relation = serializers.CharField()
    is_primary = serializers.BooleanField()
    can_pickup = serializers.BooleanField()
    receives_sms = serializers.BooleanField()
    financial_responsible = serializers.BooleanField()
    enrollment = serializers.SerializerMethodField()

    def get_enrollment(self, obj: Any) -> dict[str, Any] | None:
        student: Student = obj["student"]
        latest = (
            student.enrollments.filter(status="active")
            .select_related("session", "class_level", "section")
            .order_by("-session__start_date")
            .first()
        )
        if latest:
            return {
                "session_name": latest.session.name,
                "class_name": latest.class_level.name,
                "section_name": latest.section.name,
                "roll_no": latest.roll_no,
            }
        return None
