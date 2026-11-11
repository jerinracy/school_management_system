"""Serializers for Staff, Leave, and Teacher Assignment modules."""

from rest_framework import serializers

from apps.core.utils.phone import normalize_bd_phone
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


class StaffListSerializer(serializers.ModelSerializer):
    """Lightweight roster view of employee profiles."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)

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
            "staff_type",
            "phone",
            "email",
            "status",
            "is_mpo",
            "joining_date",
            "photo",
        ]
        read_only_fields = ["id", "employee_id"]


class StaffCreateUpdateSerializer(serializers.ModelSerializer):
    """Full serialization for staff profile onboarding and mutation."""

    phone = serializers.CharField()
    alt_phone = serializers.CharField(required=False, allow_blank=True)
    employee_id = serializers.CharField(required=False, allow_blank=True)

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
            "staff_type",
            "status",
            "is_mpo",
            "mpo_index_number",
            "tin_number",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
        ]
        read_only_fields = ["id"]

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)

    def validate_alt_phone(self, value: str) -> str:
        if value:
            return normalize_bd_phone(value)
        return value


class StaffDetailSerializer(StaffCreateUpdateSerializer):
    """Rich staff view with nested educations, documents, and cards."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)
    educations = StaffEducationSerializer(many=True, read_only=True)
    documents = StaffDocumentSerializer(many=True, read_only=True)
    id_cards = StaffIDCardSerializer(many=True, read_only=True)

    class Meta(StaffCreateUpdateSerializer.Meta):
        fields = StaffCreateUpdateSerializer.Meta.fields + [
            "department_name",
            "designation_title",
            "educations",
            "documents",
            "id_cards",
        ]


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
