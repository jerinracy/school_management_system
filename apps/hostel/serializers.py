"""Serializers for Hostel Management."""

from rest_framework import serializers

from apps.hostel.models import (
    Bed,
    GatePass,
    Hostel,
    HostelAllocation,
    HostelAttendance,
    HostelFeeLink,
    HostelVisitorLog,
    MealAttendance,
    MealPlan,
    Room,
)


class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = [
            "id",
            "institution",
            "branch",
            "name",
            "code",
            "hostel_type",
            "warden",
            "curfew_time",
            "address",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class HostelRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "id",
            "institution",
            "hostel",
            "room_number",
            "floor",
            "capacity",
            "monthly_fee",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = [
            "id",
            "institution",
            "room",
            "bed_number",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class HostelFeeLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelFeeLink
        fields = [
            "id",
            "institution",
            "fee_head",
            "hostel",
            "session",
            "effective_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class HostelAllocationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelAllocation
        fields = [
            "id",
            "institution",
            "session",
            "student",
            "student_name",
            "hostel",
            "hostel_name",
            "room",
            "bed",
            "hostel_fee_link",
            "allocated_date",
            "vacated_date",
            "is_active",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "hostel",
            "room",
            "vacated_date",
            "is_active",
            "created_at",
            "updated_at",
        ]


class VacateAllocationSerializer(serializers.Serializer):
    vacated_date = serializers.DateField(required=False, allow_null=True)


class HostelAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)

    class Meta:
        model = HostelAttendance
        fields = [
            "id",
            "institution",
            "hostel",
            "student",
            "student_name",
            "attendance_date",
            "event_type",
            "status",
            "recorded_at",
            "recorded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "recorded_by", "created_at", "updated_at"]


class GatePassSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = GatePass
        fields = [
            "id",
            "institution",
            "student",
            "student_name",
            "hostel",
            "hostel_name",
            "allocation",
            "reason",
            "destination",
            "expected_out_at",
            "expected_return_at",
            "actual_out_at",
            "actual_return_at",
            "guardian_confirmed_at",
            "approved_by",
            "status",
            "curfew_alert_sent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "allocation",
            "actual_out_at",
            "actual_return_at",
            "guardian_confirmed_at",
            "approved_by",
            "status",
            "curfew_alert_sent",
            "created_at",
            "updated_at",
        ]


class GatePassOtpConfirmSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=4, max_length=10)


class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = [
            "id",
            "institution",
            "hostel",
            "name",
            "meal_type",
            "menu_description",
            "unit_cost",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class MealAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealAttendance
        fields = [
            "id",
            "institution",
            "meal_plan",
            "student",
            "meal_date",
            "consumed",
            "recorded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "recorded_by", "created_at", "updated_at"]


class HostelVisitorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelVisitorLog
        fields = [
            "id",
            "institution",
            "hostel",
            "student",
            "visitor_name",
            "visitor_phone",
            "relation",
            "nid_or_id_no",
            "purpose",
            "check_in_at",
            "check_out_at",
            "recorded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "recorded_by", "created_at", "updated_at"]
