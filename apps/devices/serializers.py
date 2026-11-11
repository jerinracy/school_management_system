"""Serializers for Devices, Groups, Enrollments, Consents, Commands, and Raw Punches."""

from typing import Any

from rest_framework import serializers

from apps.devices.models import (
    BiometricConsent,
    BiometricEnrollment,
    Device,
    DeviceCommand,
    DeviceGroup,
    DeviceGroupMember,
    DeviceHealthLog,
    DeviceUserMap,
    RawPunch,
)


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for hardware terminal devices."""

    branch_name = serializers.CharField(source="branch.name_en", read_only=True)
    auth_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_token = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "institution",
            "branch",
            "branch_name",
            "name",
            "device_type",
            "vendor",
            "model",
            "serial_no",
            "protocol",
            "ip_address",
            "port",
            "auth_secret",
            "api_token",
            "location",
            "timezone_offset_minutes",
            "status",
            "last_seen",
            "firmware_version",
            "user_capacity",
            "punch_capacity",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "status", "last_seen", "created_at", "updated_at"]


class DeviceGroupMemberSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    device_serial = serializers.CharField(source="device.serial_no", read_only=True)

    class Meta:
        model = DeviceGroupMember
        fields = ["id", "group", "device", "device_name", "device_serial", "created_at"]
        read_only_fields = ["id", "created_at"]


class DeviceGroupSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = DeviceGroup
        fields = [
            "id",
            "institution",
            "name",
            "description",
            "target_audience",
            "members_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class DeviceUserMapSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)

    class Meta:
        model = DeviceUserMap
        fields = [
            "id",
            "institution",
            "device",
            "device_name",
            "device_user_id",
            "user_type",
            "student",
            "student_name",
            "staff",
            "staff_name",
            "rfid_card",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class BiometricConsentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)
    guardian_name = serializers.CharField(source="guardian.name_en", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = BiometricConsent
        fields = [
            "id",
            "institution",
            "subject_type",
            "student",
            "student_name",
            "staff",
            "staff_name",
            "guardian",
            "guardian_name",
            "consent_version",
            "granted_at",
            "withdrawn_at",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "granted_at",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        subject_type = attrs.get("subject_type")
        student = attrs.get("student")
        guardian = attrs.get("guardian")
        staff = attrs.get("staff")

        if subject_type == "student":
            if not student:
                raise serializers.ValidationError(
                    {"student": "Student is required for student consent."}
                )
            if not guardian:
                raise serializers.ValidationError(
                    {"guardian": "Guardian consent is mandatory for school students."}
                )
        elif subject_type == "staff":
            if not staff:
                raise serializers.ValidationError(
                    {"staff": "Staff member is required for staff consent."}
                )

        return attrs


class BiometricEnrollmentSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)

    class Meta:
        model = BiometricEnrollment
        fields = [
            "id",
            "institution",
            "subject_type",
            "student",
            "student_name",
            "staff",
            "staff_name",
            "device",
            "device_name",
            "method",
            "device_user_id",
            "consent",
            "enrolled_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "enrolled_at", "created_at", "updated_at"]


class EnrollUserRequestSerializer(serializers.Serializer):
    """Input serializer for terminal enrollment."""

    user_pin = serializers.CharField(max_length=50)
    user_name = serializers.CharField(max_length=100)
    card_no = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    student_id = serializers.UUIDField(required=False, allow_null=True)
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    method = serializers.CharField(max_length=30, required=False, allow_blank=True)


class DeviceCommandSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = DeviceCommand
        fields = [
            "id",
            "institution",
            "device",
            "device_name",
            "command_type",
            "payload",
            "status",
            "sent_at",
            "acknowledged_at",
            "response_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "sent_at",
            "acknowledged_at",
            "created_at",
            "updated_at",
        ]


class DeviceHealthLogSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = DeviceHealthLog
        fields = [
            "id",
            "institution",
            "device",
            "device_name",
            "device_time",
            "server_time",
            "clock_drift_seconds",
            "ip_address",
            "user_count",
            "punch_count",
            "status_ok",
            "raw_data",
            "created_at",
        ]
        read_only_fields = ["id", "server_time", "created_at"]


class RawPunchSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    student_name = serializers.CharField(source="resolved_student.name_en", read_only=True)
    staff_name = serializers.CharField(source="resolved_staff.full_name_en", read_only=True)

    class Meta:
        model = RawPunch
        fields = [
            "id",
            "institution",
            "device",
            "device_name",
            "serial_no",
            "raw_user_id",
            "device_time",
            "received_at",
            "clock_drift_seconds",
            "verify_type",
            "punch_state",
            "work_code",
            "payload_hash",
            "status",
            "resolved_student",
            "student_name",
            "resolved_staff",
            "staff_name",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class ResolveUnmappedPunchSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=False, allow_null=True)
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    create_mapping = serializers.BooleanField(default=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        student_id = attrs.get("student_id")
        staff_id = attrs.get("staff_id")
        if not student_id and not staff_id:
            raise serializers.ValidationError("Either student_id or staff_id must be provided.")
        if student_id and staff_id:
            raise serializers.ValidationError("Cannot resolve punch to both student and staff.")
        return attrs
