"""Serializers for academic structure and routines."""

from typing import Any

from rest_framework import serializers

from apps.academics.models import (
    ClassLevel,
    ClassSubject,
    Group,
    Period,
    Room,
    RoutineSlot,
    Section,
    Subject,
    SubstituteAssignment,
    Weekday,
)
from apps.academics.services.conflicts import validate_routine_slot_conflicts
from apps.institutions.models import AcademicSession, Shift


class ClassLevelSerializer(serializers.ModelSerializer):
    medium_display = serializers.CharField(source="get_medium_display", read_only=True)
    sections_count = serializers.IntegerField(source="sections.count", read_only=True)

    class Meta:
        model = ClassLevel
        fields = [
            "id",
            "name",
            "code",
            "order",
            "medium",
            "medium_display",
            "has_groups",
            "sections_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SectionSerializer(serializers.ModelSerializer):
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    teacher_name = serializers.CharField(
        source="teacher_user.full_name", read_only=True, default=None
    )

    class Meta:
        model = Section
        fields = [
            "id",
            "class_level",
            "class_level_name",
            "shift",
            "shift_name",
            "session",
            "session_name",
            "name",
            "capacity",
            "teacher_user",
            "teacher_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = self.context["request"].user.institution
        instance = self.instance if isinstance(self.instance, Section) else None
        class_level = attrs.get("class_level") or (instance.class_level if instance else None)
        shift = attrs.get("shift") or (instance.shift if instance else None)
        session = attrs.get("session") or (instance.session if instance else None)
        teacher_user = attrs.get("teacher_user") or (instance.teacher_user if instance else None)

        if class_level and class_level.institution_id != institution.id:
            raise serializers.ValidationError(
                {"class_level": "Class level must belong to your institution."}
            )
        if shift and shift.institution_id != institution.id:
            raise serializers.ValidationError({"shift": "Shift must belong to your institution."})
        if session and session.institution_id != institution.id:
            raise serializers.ValidationError(
                {"session": "Session must belong to your institution."}
            )
        if teacher_user and teacher_user.institution_id != institution.id:
            raise serializers.ValidationError(
                {"teacher_user": "Teacher must belong to your institution."}
            )

        return attrs


class BulkCreateSectionsSerializer(serializers.Serializer):
    class_level_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    names = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
        help_text="List of section names (e.g. ['A', 'B', 'C'] or ['Padma', 'Meghna'])",
    )
    capacity = serializers.IntegerField(default=50, min_value=1)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = self.context["request"].user.institution
        try:
            attrs["class_level"] = ClassLevel.objects.get(
                id=attrs["class_level_id"], institution=institution
            )
        except ClassLevel.DoesNotExist:
            raise serializers.ValidationError(
                {"class_level_id": "Class level not found in your institution."}
            ) from None

        try:
            attrs["shift"] = Shift.objects.get(id=attrs["shift_id"], institution=institution)
        except Shift.DoesNotExist:
            raise serializers.ValidationError(
                {"shift_id": "Shift not found in your institution."}
            ) from None

        try:
            attrs["session"] = AcademicSession.objects.get(
                id=attrs["session_id"], institution=institution
            )
        except AcademicSession.DoesNotExist:
            raise serializers.ValidationError(
                {"session_id": "Academic session not found in your institution."}
            ) from None

        return attrs


class SubjectSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Subject
        fields = [
            "id",
            "code",
            "name_bn",
            "name_en",
            "type",
            "type_display",
            "has_papers",
            "paper_number",
            "marks_components_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClassSubjectSerializer(serializers.ModelSerializer):
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    subject_name_en = serializers.CharField(source="subject.name_en", read_only=True)
    subject_name_bn = serializers.CharField(source="subject.name_bn", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = ClassSubject
        fields = [
            "id",
            "class_level",
            "class_level_name",
            "group",
            "group_name",
            "session",
            "session_name",
            "subject",
            "subject_code",
            "subject_name_en",
            "subject_name_bn",
            "full_marks",
            "pass_rule",
            "credit_weight",
            "is_optional_elective",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RoomSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)

    class Meta:
        model = Room
        fields = [
            "id",
            "branch",
            "branch_name",
            "name",
            "capacity",
            "type",
            "type_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PeriodSerializer(serializers.ModelSerializer):
    shift_name = serializers.CharField(source="shift.name", read_only=True)

    class Meta:
        model = Period
        fields = [
            "id",
            "shift",
            "shift_name",
            "name",
            "start_time",
            "end_time",
            "order",
            "is_break",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance if isinstance(self.instance, Period) else None
        start = attrs.get("start_time") or (instance.start_time if instance else None)
        end = attrs.get("end_time") or (instance.end_time if instance else None)
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class RoutineSlotSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    period_start = serializers.TimeField(source="period.start_time", read_only=True)
    period_end = serializers.TimeField(source="period.end_time", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    subject_name_en = serializers.CharField(source="subject.name_en", read_only=True)
    teacher_name = serializers.CharField(
        source="teacher_user.full_name", read_only=True, default=None
    )
    room_name = serializers.CharField(source="room.name", read_only=True, default=None)
    section_name = serializers.CharField(source="section.name", read_only=True)
    class_level_name = serializers.CharField(source="section.class_level.name", read_only=True)

    class Meta:
        model = RoutineSlot
        fields = [
            "id",
            "section",
            "section_name",
            "class_level_name",
            "weekday",
            "weekday_display",
            "period",
            "period_name",
            "period_start",
            "period_end",
            "subject",
            "subject_code",
            "subject_name_en",
            "teacher_user",
            "teacher_name",
            "room",
            "room_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = self.context["request"].user.institution
        instance = self.instance if isinstance(self.instance, RoutineSlot) else None
        section = attrs.get("section") or (instance.section if instance else None)
        period = attrs.get("period") or (instance.period if instance else None)
        weekday = (
            attrs.get("weekday") if "weekday" in attrs else (instance.weekday if instance else None)
        )
        teacher_user = (
            attrs.get("teacher_user")
            if "teacher_user" in attrs
            else (instance.teacher_user if instance else None)
        )
        room = attrs.get("room") if "room" in attrs else (instance.room if instance else None)

        if not section or not period or weekday is None:
            return attrs

        report = validate_routine_slot_conflicts(
            institution_id=institution.id,
            section_id=section.id,
            weekday=weekday,
            period_id=period.id,
            teacher_user_id=teacher_user.id if teacher_user else None,
            room_id=room.id if room else None,
            exclude_slot_id=instance.id if instance else None,
        )

        if not report.is_valid:
            error_dict: dict[str, list[str]] = {}
            for conflict in report.conflicts:
                error_dict.setdefault(conflict.field, []).append(conflict.message)
            raise serializers.ValidationError(error_dict)

        return attrs


class RoutineValidationInputSerializer(serializers.Serializer):
    section_id = serializers.UUIDField()
    weekday = serializers.ChoiceField(choices=Weekday.choices)
    period_id = serializers.UUIDField()
    teacher_user_id = serializers.UUIDField(required=False, allow_null=True)
    room_id = serializers.UUIDField(required=False, allow_null=True)
    exclude_slot_id = serializers.UUIDField(required=False, allow_null=True)


class CopySessionInputSerializer(serializers.Serializer):
    source_session_id = serializers.UUIDField(help_text="UUID of source session to copy from")
    target_session_id = serializers.UUIDField(help_text="UUID of target session to copy into")
    copy_sections = serializers.BooleanField(default=True)
    copy_class_subjects = serializers.BooleanField(default=True)
    copy_routine = serializers.BooleanField(default=False)
    preserve_teachers = serializers.BooleanField(default=False)
    dry_run = serializers.BooleanField(default=True, help_text="True to simulate without saving")


class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    substitute_teacher_name = serializers.CharField(
        source="substitute_teacher.full_name", read_only=True
    )
    original_teacher_name = serializers.CharField(
        source="original_teacher.full_name", read_only=True, default=None
    )
    routine_summary = serializers.CharField(source="routine_slot.__str__", read_only=True)

    class Meta:
        model = SubstituteAssignment
        fields = [
            "id",
            "routine_slot",
            "routine_summary",
            "slot_date",
            "original_teacher",
            "original_teacher_name",
            "substitute_teacher",
            "substitute_teacher_name",
            "reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = self.context["request"].user.institution
        instance = self.instance if isinstance(self.instance, SubstituteAssignment) else None
        substitute = attrs.get("substitute_teacher") or (
            instance.substitute_teacher if instance else None
        )
        original = attrs.get("original_teacher") or (
            instance.original_teacher if instance else None
        )
        routine_slot = attrs.get("routine_slot") or (instance.routine_slot if instance else None)

        if substitute and substitute.institution_id != institution.id:
            raise serializers.ValidationError(
                {"substitute_teacher": "Substitute teacher must belong to your institution."}
            )
        if routine_slot and routine_slot.institution_id != institution.id:
            raise serializers.ValidationError(
                {"routine_slot": "Routine slot must belong to your institution."}
            )
        if substitute and original and substitute.id == original.id:
            raise serializers.ValidationError(
                {"substitute_teacher": "Substitute teacher cannot be the original teacher."}
            )

        return attrs
