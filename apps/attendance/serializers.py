"""DRF Serializers for attendance policies, daily records, period tracking, and mobile check-ins."""

from typing import Any

from rest_framework import serializers

from apps.attendance.models import (
    AttendanceCorrection,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceStatus,
    DailyAttendance,
    MobileCheckin,
    PeriodAttendance,
    PeriodAttendanceStatus,
    PolicyAssignment,
)


class AttendancePolicySerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    class_name = serializers.CharField(source="class_level.name", read_only=True)

    class Meta:
        model = AttendancePolicy
        fields = [
            "id",
            "institution",
            "name",
            "user_type",
            "branch",
            "branch_name",
            "shift",
            "shift_name",
            "class_level",
            "class_name",
            "start_time",
            "end_time",
            "grace_minutes",
            "late_threshold_minutes",
            "half_day_threshold_minutes",
            "early_leave_threshold_minutes",
            "min_work_duration_minutes",
            "multi_punch_mode",
            "duplicate_window_seconds",
            "allowed_methods",
            "weekend_days",
            "geofence_latitude",
            "geofence_longitude",
            "geofence_radius_meters",
            "version",
            "effective_from",
            "effective_to",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "version", "created_at", "updated_at"]


class PolicySimulateRequestSerializer(serializers.Serializer):
    """Input serializer for dry-running policy computation on sample punches."""

    target_date = serializers.DateField()
    punches = serializers.ListField(child=serializers.DateTimeField(), allow_empty=True)
    is_holiday = serializers.BooleanField(default=False)
    is_weekend = serializers.BooleanField(default=False)
    has_approved_leave = serializers.BooleanField(default=False)


class PolicySimulateResultSerializer(serializers.Serializer):
    """Output serializer for simulated attendance outcome."""

    status = serializers.CharField()
    first_in = serializers.DateTimeField(allow_null=True)
    last_out = serializers.DateTimeField(allow_null=True)
    total_minutes = serializers.IntegerField()
    minutes_late = serializers.IntegerField()
    minutes_early_leave = serializers.IntegerField()
    remarks = serializers.CharField(allow_blank=True)


class PolicyAssignmentSerializer(serializers.ModelSerializer):
    policy_name = serializers.CharField(source="policy.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)

    class Meta:
        model = PolicyAssignment
        fields = [
            "id",
            "institution",
            "policy",
            "policy_name",
            "user_type",
            "branch",
            "branch_name",
            "shift",
            "shift_name",
            "class_level",
            "section",
            "priority",
            "created_at",
        ]
        read_only_fields = ["id", "institution", "created_at"]


class AttendanceEventSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = AttendanceEvent
        fields = [
            "id",
            "institution",
            "user_type",
            "student",
            "student_name",
            "staff",
            "staff_name",
            "direction",
            "method",
            "device",
            "device_name",
            "timestamp",
            "source",
            "is_processed",
            "created_at",
        ]
        read_only_fields = fields


class DailyAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_roll = serializers.CharField(source="student.student_id", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)
    staff_employee_id = serializers.CharField(source="staff.employee_id", read_only=True)
    policy_name = serializers.CharField(source="policy.name", read_only=True)

    class Meta:
        model = DailyAttendance
        fields = [
            "id",
            "institution",
            "date",
            "user_type",
            "student",
            "student_name",
            "student_roll",
            "staff",
            "staff_name",
            "staff_employee_id",
            "status",
            "first_in",
            "last_out",
            "total_minutes",
            "minutes_late",
            "minutes_early_leave",
            "policy",
            "policy_name",
            "policy_version",
            "is_overridden",
            "override_reason",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ManualAttendanceItemSerializer(serializers.Serializer):
    person_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=AttendanceStatus.choices)
    remarks = serializers.CharField(required=False, allow_blank=True, default="Manual entry")


class BulkManualAttendanceSerializer(serializers.Serializer):
    date = serializers.DateField()
    user_type = serializers.ChoiceField(choices=[("student", "Student"), ("staff", "Staff")])
    records = serializers.ListField(child=ManualAttendanceItemSerializer(), min_length=1)


class PeriodAttendanceSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source="section.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name_en", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name_en", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)

    class Meta:
        model = PeriodAttendance
        fields = [
            "id",
            "institution",
            "date",
            "section",
            "section_name",
            "routine_slot",
            "subject",
            "subject_name",
            "teacher",
            "teacher_name",
            "student",
            "student_name",
            "status",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class PeriodAttendanceStudentItemSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=PeriodAttendanceStatus.choices, default=PeriodAttendanceStatus.PRESENT
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PeriodAttendanceBulkSubmitSerializer(serializers.Serializer):
    date = serializers.DateField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    routine_slot_id = serializers.UUIDField(required=False, allow_null=True)
    records = serializers.ListField(child=PeriodAttendanceStudentItemSerializer(), min_length=1)


class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.get_full_name", read_only=True)
    student_name = serializers.CharField(source="daily_attendance.student.name_en", read_only=True)
    staff_name = serializers.CharField(source="daily_attendance.staff.full_name_en", read_only=True)
    target_date = serializers.DateField(source="daily_attendance.date", read_only=True)

    class Meta:
        model = AttendanceCorrection
        fields = [
            "id",
            "institution",
            "daily_attendance",
            "target_date",
            "student_name",
            "staff_name",
            "requested_by",
            "requested_by_name",
            "reason",
            "status_before",
            "status_after",
            "time_in_before",
            "time_in_after",
            "time_out_before",
            "time_out_after",
            "approval_status",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "requested_by",
            "status_before",
            "time_in_before",
            "time_out_before",
            "approval_status",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]


class AttendanceCorrectionCreateSerializer(serializers.Serializer):
    daily_attendance_id = serializers.UUIDField()
    reason = serializers.CharField(min_length=5)
    status_after = serializers.ChoiceField(choices=AttendanceStatus.choices)
    time_in_after = serializers.DateTimeField(required=False, allow_null=True)
    time_out_after = serializers.DateTimeField(required=False, allow_null=True)


class AttendanceCorrectionDecideSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")


class MobileCheckinSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = MobileCheckin
        fields = [
            "id",
            "institution",
            "user",
            "user_name",
            "staff",
            "latitude",
            "longitude",
            "accuracy_meters",
            "is_within_geofence",
            "geofence_distance_meters",
            "selfie_image",
            "device_info",
            "timestamp",
            "attendance_event",
            "created_at",
        ]
        read_only_fields = fields


class MobileCheckinCreateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy_meters = serializers.FloatField(default=10.0)
    selfie_image = serializers.ImageField(required=False, allow_null=True)
    device_info = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    timestamp = serializers.DateTimeField(required=False)


class RecomputeAttendanceRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    user_type = serializers.ChoiceField(
        choices=[("student", "Student"), ("staff", "Staff"), ("all", "All")], default="all"
    )
    student_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
    staff_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "end_date cannot be earlier than start_date."}
            )
        return attrs
