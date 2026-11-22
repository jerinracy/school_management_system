"""Serializers for Guardians, Families, and Authorized Pickups."""

from typing import Any

from django.db import transaction
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
    student_id_number = serializers.CharField(source="student.student_id", read_only=True)
    guardian_name = serializers.CharField(source="guardian.name_en", read_only=True)
    guardian_phone = serializers.CharField(source="guardian.phone", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            "id",
            "student",
            "student_name",
            "student_id_number",
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


class StudentLinkInputSerializer(serializers.Serializer):
    """Input payload for linking a student during guardian creation/update."""

    student_id = serializers.UUIDField()
    relation = serializers.ChoiceField(
        choices=GuardianRelation.choices, default=GuardianRelation.FATHER
    )
    is_primary = serializers.BooleanField(default=False)
    can_pickup = serializers.BooleanField(default=True)
    receives_sms = serializers.BooleanField(default=True)
    financial_responsible = serializers.BooleanField(default=False)


class GuardianSerializer(serializers.ModelSerializer):
    """Standard serializer for Guardian profiles."""

    phone = serializers.CharField()
    alt_phone = serializers.CharField(required=False, allow_blank=True)
    has_portal_account = serializers.SerializerMethodField()
    give_portal_access = serializers.BooleanField(required=False, default=False, write_only=True)
    initial_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    student_links = StudentLinkInputSerializer(many=True, required=False, write_only=True)
    student_relations = StudentGuardianSerializer(many=True, read_only=True)

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
            "student_links",
            "student_relations",
            "give_portal_access",
            "initial_password",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "has_portal_account",
            "student_relations",
            "created_at",
            "updated_at",
        ]

    def get_has_portal_account(self, obj: Guardian) -> bool:
        return obj.user_id is not None

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)

    def validate_alt_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Guardian:
        give_portal = validated_data.pop("give_portal_access", False)
        initial_password = validated_data.pop("initial_password", None)
        student_links_data = validated_data.pop("student_links", [])
        guardian = super().create(validated_data)
        institution = guardian.institution

        if institution and student_links_data:
            from apps.guardians.services.guardian_service import link_student_guardian

            for link_data in student_links_data:
                student = Student.objects.filter(
                    id=link_data["student_id"],
                    institution=institution,
                ).first()
                if student:
                    link_student_guardian(
                        institution=institution,
                        student=student,
                        guardian=guardian,
                        relation=link_data.get("relation", guardian.relation_default),
                        is_primary=link_data.get("is_primary", False),
                        can_pickup=link_data.get("can_pickup", True),
                        receives_sms=link_data.get("receives_sms", True),
                        financial_responsible=link_data.get("financial_responsible", False),
                    )

        if give_portal:
            from apps.guardians.services.guardian_service import create_portal_user_for_guardian

            create_portal_user_for_guardian(
                guardian, password=initial_password, phone=guardian.phone
            )

        return guardian

    @transaction.atomic
    def update(self, instance: Guardian, validated_data: dict[str, Any]) -> Guardian:
        give_portal = validated_data.pop("give_portal_access", False)
        initial_password = validated_data.pop("initial_password", None)
        student_links_data = validated_data.pop("student_links", None)

        old_phone = instance.phone
        guardian = super().update(instance, validated_data)

        # Sync phone with linked user if changed
        if guardian.user and guardian.phone and guardian.phone != old_phone:
            guardian.user.phone = guardian.phone
            guardian.user.save(update_fields=["phone"])

        if student_links_data is not None and guardian.institution:
            from apps.guardians.services.guardian_service import link_student_guardian

            for link_data in student_links_data:
                student = Student.objects.filter(
                    id=link_data["student_id"],
                    institution=guardian.institution,
                ).first()
                if student:
                    link_student_guardian(
                        institution=guardian.institution,
                        student=student,
                        guardian=guardian,
                        relation=link_data.get("relation", guardian.relation_default),
                        is_primary=link_data.get("is_primary", False),
                        can_pickup=link_data.get("can_pickup", True),
                        receives_sms=link_data.get("receives_sms", True),
                        financial_responsible=link_data.get("financial_responsible", False),
                    )

        if give_portal and not guardian.user:
            from apps.guardians.services.guardian_service import create_portal_user_for_guardian

            create_portal_user_for_guardian(
                guardian, password=initial_password, phone=guardian.phone
            )

        return guardian


class GuardianDetailSerializer(GuardianSerializer):
    """Detailed guardian serializer embedding linked students."""

    class Meta(GuardianSerializer.Meta):
        fields = GuardianSerializer.Meta.fields


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
                "class_level_id": str(latest.class_level.id) if latest.class_level else None,
                "section_name": latest.section.name,
                "section_id": str(latest.section.id) if latest.section else None,
                "roll_no": latest.roll_no,
            }
        return None


class GuardianAssignLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=6, required=False, allow_blank=True)

    def validate_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value
