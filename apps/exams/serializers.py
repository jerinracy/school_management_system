"""DRF Serializers for exams, routines, seat plans, admit cards, and mark entries."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.exams.models import (
    AdmitCard,
    Exam,
    ExamEligibilityPolicy,
    ExamRoutine,
    ExamSubject,
    ExamType,
    GraceMarkRule,
    MarkEntry,
    MarkEntryLog,
    ReScrutinyRequest,
    ReScrutinyStatus,
    SeatPlan,
    StudentExamEligibility,
)


class ExamTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamType
        fields = [
            "id",
            "name",
            "code",
            "is_board_exam",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context.get("request")
        institution = getattr(request.user, "institution", None) if request else None
        code = attrs.get("code")
        if code and institution:
            code = code.strip().upper()
            attrs["code"] = code
            qs = ExamType.objects.filter(institution=institution, code=code)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": f"Exam type with code '{code}' already exists."}
                )
        return attrs


class ExamSubjectSerializer(serializers.ModelSerializer):
    subject_name_en = serializers.CharField(source="subject.name_en", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    assigned_teacher_name = serializers.CharField(
        source="assigned_teacher.full_name_en", read_only=True, default=None
    )

    class Meta:
        model = ExamSubject
        fields = [
            "id",
            "exam",
            "class_level",
            "class_level_name",
            "subject",
            "subject_name_en",
            "subject_code",
            "exam_date",
            "start_time",
            "end_time",
            "room",
            "full_marks",
            "pass_marks",
            "creative_full_marks",
            "creative_pass_marks",
            "mcq_full_marks",
            "mcq_pass_marks",
            "practical_full_marks",
            "practical_pass_marks",
            "is_combined_paper",
            "combined_with",
            "assigned_teacher",
            "assigned_teacher_name",
            "is_marks_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_marks_locked", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        full_marks = attrs.get(
            "full_marks", getattr(self.instance, "full_marks", Decimal("100.00"))
        )
        cq = attrs.get(
            "creative_full_marks", getattr(self.instance, "creative_full_marks", Decimal("70.00"))
        )
        mcq = attrs.get(
            "mcq_full_marks", getattr(self.instance, "mcq_full_marks", Decimal("30.00"))
        )
        prac = attrs.get(
            "practical_full_marks", getattr(self.instance, "practical_full_marks", Decimal("0.00"))
        )

        total = cq + mcq + prac
        if total != full_marks:
            raise serializers.ValidationError(
                f"Sum of component full marks ({total}) must equal subject full marks ({full_marks})."
            )
        return attrs


class ExamSerializer(serializers.ModelSerializer):
    exam_type_name = serializers.CharField(source="exam_type.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    exam_subjects_count = serializers.IntegerField(source="exam_subjects.count", read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "exam_type",
            "exam_type_name",
            "session",
            "session_name",
            "name",
            "term",
            "start_date",
            "end_date",
            "weightage",
            "status",
            "target_classes",
            "publish_date",
            "is_active",
            "exam_subjects_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start > end:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        return attrs


class ExamRoutineSerializer(serializers.ModelSerializer):
    subject_name_en = serializers.CharField(source="exam_subject.subject.name_en", read_only=True)
    class_level_name = serializers.CharField(source="exam_subject.class_level.name", read_only=True)

    class Meta:
        model = ExamRoutine
        fields = [
            "id",
            "exam",
            "exam_subject",
            "subject_name_en",
            "class_level_name",
            "exam_date",
            "start_time",
            "end_time",
            "room_number",
            "instructions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExamEligibilityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamEligibilityPolicy
        fields = [
            "id",
            "exam",
            "min_attendance_percentage",
            "non_collegiate_threshold",
            "allow_non_collegiate",
            "require_fee_clearance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentExamEligibilitySerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True)

    class Meta:
        model = StudentExamEligibility
        fields = [
            "id",
            "exam",
            "student",
            "student_id",
            "student_name_en",
            "student_name_bn",
            "attendance_percentage",
            "dues_cleared",
            "clearance_status",
            "clearance_notes",
            "evaluated_at",
        ]
        read_only_fields = ["id", "evaluated_at"]


class SeatPlanSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    class_name = serializers.CharField(source="class_level.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True, default=None)

    class Meta:
        model = SeatPlan
        fields = [
            "id",
            "exam",
            "exam_subject",
            "room_number",
            "bench_label",
            "seat_number",
            "student",
            "student_id",
            "student_name",
            "roll_number",
            "class_level",
            "class_name",
            "section",
            "section_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SeatPlanGenerateSerializer(serializers.Serializer):
    room_configs = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of room configurations e.g. [{'room_number': '101', 'bench_count': 20, 'seats_per_bench': 2}]",
    )
    interleave = serializers.BooleanField(
        default=True, help_text="Interleave different classes on benches"
    )
    exam_subject_id = serializers.UUIDField(required=False, allow_null=True)


class AdmitCardSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    student_name_bn = serializers.CharField(source="student.name_bn", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = AdmitCard
        fields = [
            "id",
            "exam",
            "exam_name",
            "student",
            "student_id",
            "student_name_en",
            "student_name_bn",
            "card_number",
            "issue_date",
            "is_issued",
            "generated_at",
        ]
        read_only_fields = ["id", "generated_at"]


class MarkEntryLogSerializer(serializers.ModelSerializer):
    modified_by_username = serializers.CharField(
        source="modified_by.username", read_only=True, default=None
    )

    class Meta:
        model = MarkEntryLog
        fields = [
            "id",
            "mark_entry",
            "modified_by",
            "modified_by_username",
            "field_name",
            "old_value",
            "new_value",
            "reason",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]


class MarkEntrySerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    student_name_en = serializers.CharField(source="student.name_en", read_only=True)
    entered_by_username = serializers.CharField(
        source="entered_by.username", read_only=True, default=None
    )

    class Meta:
        model = MarkEntry
        fields = [
            "id",
            "exam_subject",
            "student",
            "student_id",
            "student_name_en",
            "creative_marks",
            "mcq_marks",
            "practical_marks",
            "total_marks",
            "is_absent",
            "is_locked",
            "entered_by",
            "entered_by_username",
            "locked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_marks",
            "is_locked",
            "locked_at",
            "created_at",
            "updated_at",
        ]


class BulkMarkItemSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    creative_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    mcq_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    practical_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    is_absent = serializers.BooleanField(default=False)
    reason = serializers.CharField(required=False, default="")


class BulkMarkSubmitSerializer(serializers.Serializer):
    exam_subject_id = serializers.UUIDField()
    entries = serializers.ListField(child=BulkMarkItemSerializer())


class MarkLockSerializer(serializers.Serializer):
    exam_subject_id = serializers.UUIDField()


class MarkUnlockSerializer(serializers.Serializer):
    exam_subject_id = serializers.UUIDField()
    reason = serializers.CharField(min_length=5, help_text="Reason for administrative unlock")


class ReScrutinyRequestSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    subject_name = serializers.CharField(source="exam_subject.subject.name_en", read_only=True)

    class Meta:
        model = ReScrutinyRequest
        fields = [
            "id",
            "student",
            "student_id",
            "student_name",
            "exam_subject",
            "subject_name",
            "requested_by",
            "previous_creative_marks",
            "previous_mcq_marks",
            "previous_practical_marks",
            "revised_creative_marks",
            "revised_mcq_marks",
            "revised_practical_marks",
            "status",
            "fee_paid",
            "reviewer_notes",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ReScrutinyCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    exam_subject_id = serializers.UUIDField()
    fee_paid = serializers.BooleanField(default=False)


class ReScrutinyReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[ReScrutinyStatus.REVIEWED, ReScrutinyStatus.APPROVED, ReScrutinyStatus.REJECTED]
    )
    revised_creative_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    revised_mcq_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    revised_practical_marks = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    reviewer_notes = serializers.CharField(required=False, default="")


class GraceMarkRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraceMarkRule
        fields = [
            "id",
            "exam",
            "subject",
            "max_grace_marks",
            "condition_desc",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
