"""Serializers for Staff, Leave, and Teacher Assignment modules."""

from typing import Any

from django.db import transaction
from rest_framework import serializers

from apps.core.utils.phone import normalize_bd_phone
from apps.institutions.models import Branch
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
from apps.staff.services.staff_service import create_portal_user_for_staff


class DepartmentSerializer(serializers.ModelSerializer):
    """Department master data serializer."""

    head_name = serializers.CharField(source="head_of_department.full_name_en", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "code",
            "description",
            "head_of_department",
            "head_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DesignationSerializer(serializers.ModelSerializer):
    """Designation master data serializer."""

    class Meta:
        model = Designation
        fields = [
            "id",
            "title",
            "title_bn",
            "code",
            "rank_order",
            "role_category",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StaffEducationSerializer(serializers.ModelSerializer):
    """Staff degree qualification serializer."""

    class Meta:
        model = StaffEducation
        fields = [
            "id",
            "degree_title",
            "institution_name",
            "board_or_university",
            "passing_year",
            "result",
        ]
        read_only_fields = ["id"]


class StaffDocumentSerializer(serializers.ModelSerializer):
    """Staff archival document serializer."""

    class Meta:
        model = StaffDocument
        fields = [
            "id",
            "document_type",
            "title",
            "file",
            "verified",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StaffIDCardSerializer(serializers.ModelSerializer):
    """Staff identification badge serializer."""

    class Meta:
        model = StaffIDCard
        fields = [
            "id",
            "card_number",
            "issue_date",
            "expiry_date",
            "is_active",
            "rfid_uid",
            "qr_payload",
        ]
        read_only_fields = ["id"]


class ProvisionPortalAccountSerializer(serializers.Serializer):
    """Payload to create or provision portal login credentials for an employee."""

    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(
        required=False, allow_blank=True, min_length=6, write_only=True
    )


class ResetPasswordSerializer(serializers.Serializer):
    """Payload to reset a user's portal login password."""

    password = serializers.CharField(min_length=6, write_only=True)


class StaffListSerializer(serializers.ModelSerializer):
    """Lightweight roster view of employee profiles."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True, default=None)
    user_type = serializers.CharField(source="user.user_type", read_only=True, default=None)
    username = serializers.CharField(source="user.username", read_only=True, default=None)
    has_portal_access = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "id",
            "employee_id",
            "full_name_en",
            "full_name_bn",
            "department",
            "department_name",
            "designation",
            "designation_title",
            "branch",
            "branch_name",
            "staff_type",
            "user_id",
            "user_type",
            "username",
            "has_portal_access",
            "phone",
            "email",
            "status",
            "is_mpo",
            "joining_date",
            "photo",
        ]
        read_only_fields = ["id", "employee_id"]

    def get_has_portal_access(self, obj: Staff) -> bool:
        return obj.user_id is not None


class StaffCreateUpdateSerializer(serializers.ModelSerializer):
    """Full serialization for staff profile onboarding and mutation."""

    phone = serializers.CharField()
    alt_phone = serializers.CharField(required=False, allow_blank=True)
    employee_id = serializers.CharField(required=False, allow_blank=True)
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), required=False, allow_null=True
    )
    give_portal_access = serializers.BooleanField(required=False, default=False, write_only=True)
    portal_username = serializers.CharField(required=False, allow_blank=True, write_only=True)
    portal_password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Staff
        fields = [
            "id",
            "employee_id",
            "full_name_en",
            "full_name_bn",
            "gender",
            "dob",
            "blood_group",
            "phone",
            "alt_phone",
            "email",
            "nid",
            "present_address",
            "permanent_address",
            "photo",
            "joining_date",
            "confirmation_date",
            "department",
            "designation",
            "branch",
            "staff_type",
            "status",
            "is_mpo",
            "mpo_index_number",
            "tin_number",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "give_portal_access",
            "portal_username",
            "portal_password",
        ]
        read_only_fields = ["id"]

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)

    def validate_alt_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value

    def create(self, validated_data: dict[str, Any]) -> Staff:
        give_portal = validated_data.pop("give_portal_access", False)
        portal_username = validated_data.pop("portal_username", None)
        portal_password = validated_data.pop("portal_password", None)

        branch = validated_data.get("branch")
        if branch and getattr(branch, "institution", None):
            validated_data["institution"] = branch.institution

        staff = super().create(validated_data)

        if give_portal:
            create_portal_user_for_staff(
                staff,
                username=portal_username,
                password=portal_password,
            )

        return staff

    @transaction.atomic
    def update(self, instance: Staff, validated_data: dict[str, Any]) -> Staff:
        give_portal = validated_data.pop("give_portal_access", False)
        portal_username = validated_data.pop("portal_username", None)
        portal_password = validated_data.pop("portal_password", None)

        branch = validated_data.get("branch")
        if branch and getattr(branch, "institution", None):
            validated_data["institution"] = branch.institution

        old_phone = instance.phone
        old_email = instance.email
        staff = super().update(instance, validated_data)

        # Sync user phone/email if linked
        if staff.user:
            user_updated = False
            if staff.phone and staff.phone != old_phone:
                staff.user.phone = staff.phone
                user_updated = True
            if staff.email and staff.email != old_email:
                staff.user.email = staff.email
                user_updated = True
            if user_updated:
                staff.user.save(update_fields=["phone", "email"])

        if give_portal and not staff.user:
            create_portal_user_for_staff(
                staff,
                username=portal_username,
                password=portal_password,
            )

        return staff


class StaffDetailSerializer(StaffCreateUpdateSerializer):
    """Rich staff view with nested educations, documents, and cards."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True, default=None)
    username = serializers.CharField(source="user.username", read_only=True, default=None)
    user_type = serializers.CharField(source="user.user_type", read_only=True, default=None)
    has_portal_access = serializers.SerializerMethodField()
    shift_name = serializers.SerializerMethodField()
    educations = StaffEducationSerializer(many=True, read_only=True)
    documents = StaffDocumentSerializer(many=True, read_only=True)
    id_cards = StaffIDCardSerializer(many=True, read_only=True)

    class Meta(StaffCreateUpdateSerializer.Meta):
        fields = StaffCreateUpdateSerializer.Meta.fields + [
            "department_name",
            "designation_title",
            "branch_name",
            "user_id",
            "username",
            "user_type",
            "has_portal_access",
            "shift_name",
            "educations",
            "documents",
            "id_cards",
        ]

    def get_has_portal_access(self, obj: Staff) -> bool:
        return bool(obj.user)

    def get_shift_name(self, obj: Staff) -> str | None:
        section = obj.managed_sections.select_related("shift").first()
        if section and section.shift:
            return section.shift.name
        slot = obj.routine_slots.select_related("section__shift").first()
        if slot and slot.section and slot.section.shift:
            return slot.section.shift.name
        return None


class StaffPhotoUploadSerializer(serializers.ModelSerializer):
    """Serializer for updating staff profile photo."""

    photo = serializers.FileField(required=True)

    class Meta:
        model = Staff
        fields = ["photo"]


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Institutional leave type configuration serializer."""

    class Meta:
        model = LeaveType
        fields = [
            "id",
            "name",
            "name_bn",
            "code",
            "yearly_quota",
            "is_paid",
            "allow_carry_forward",
            "max_carry_forward_days",
            "gender_restriction",
        ]
        read_only_fields = ["id"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Employee annual leave quota balance serializer."""

    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "staff",
            "staff_name",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "session",
            "session_name",
            "allocated_days",
            "carried_forward_days",
            "used_days",
            "pending_days",
            "remaining_days",
        ]
        read_only_fields = ["id", "remaining_days"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Leave application lifecycle serializer."""

    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    recommender_name = serializers.CharField(source="recommender.full_name_en", read_only=True)
    approver_name = serializers.CharField(source="approver.full_name_en", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "staff",
            "staff_name",
            "leave_type",
            "leave_type_code",
            "session",
            "session_name",
            "start_date",
            "end_date",
            "days_count",
            "reason",
            "status",
            "emergency_phone",
            "attachment",
            "recommender_name",
            "approver_name",
            "rejection_reason",
            "decided_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "days_count",
            "status",
            "recommender_name",
            "approver_name",
            "rejection_reason",
            "decided_at",
            "created_at",
        ]


class LeaveApplyActionSerializer(serializers.Serializer):
    """Payload to submit a leave request."""

    staff_id = serializers.UUIDField(required=False)
    leave_type_id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    emergency_phone = serializers.CharField(required=False, allow_blank=True)
    attachment = serializers.FileField(required=False, allow_null=True)


class LeaveDecideActionSerializer(serializers.Serializer):
    """Payload to recommend, approve, or reject a leave application."""

    reason = serializers.CharField(required=False, allow_blank=True)


class TeacherAssignmentSerializer(serializers.ModelSerializer):
    """Instructor class/subject mapping serializer."""

    teacher_name = serializers.CharField(source="teacher.full_name_en", read_only=True)
    subject_name = serializers.CharField(source="subject.name_en", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    class_name = serializers.CharField(source="section.class_level.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = TeacherAssignment
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "subject",
            "subject_name",
            "section",
            "section_name",
            "class_name",
            "session",
            "session_name",
            "periods_per_week",
            "is_primary_teacher",
        ]
        read_only_fields = ["id"]


class WorkloadSummarySerializer(serializers.Serializer):
    """Computed instructor teaching metrics serializer."""

    teacher_id = serializers.UUIDField()
    teacher_name = serializers.CharField()
    employee_id = serializers.CharField()
    total_assigned_periods = serializers.IntegerField()
    total_routine_slots_per_week = serializers.IntegerField()
    unique_subjects_count = serializers.IntegerField()
    unique_sections_count = serializers.IntegerField()
    assignments = serializers.ListField(child=serializers.DictField())
