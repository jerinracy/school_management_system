"""Serializers for academic structure and routines."""

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.academics.models import (
    ClassLevel,
    ClassSubject,
    Group,
    Period,
    Room,
    RoomType,
    RoutineSlot,
    Section,
    Subject,
    SubjectType,
    SubstituteAssignment,
    Weekday,
)
from apps.academics.services.conflicts import validate_routine_slot_conflicts
from apps.core.mixins import get_request_institution
from apps.institutions.models import AcademicSession, Shift
from apps.staff.models import Staff

User = get_user_model()


class ClassLevelSerializer(serializers.ModelSerializer):
    medium_display = serializers.CharField(source="get_medium_display", read_only=True)
    sections_count = serializers.IntegerField(source="sections.count", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True, default=None)
    session_name = serializers.CharField(source="session.name", read_only=True, default=None)

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
            "shift",
            "shift_name",
            "session",
            "session_name",
            "branch",
            "sections_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """Support both 'order' and legacy/frontend 'numeric_order' aliases."""
        if isinstance(data, dict):
            data = dict(data)
            if "order" not in data and "numeric_order" in data:
                data["order"] = data["numeric_order"]
        return super().to_internal_value(data)


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
    teacher_staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(), required=False, allow_null=True
    )
    teacher_staff_name = serializers.CharField(
        source="teacher_staff.full_name_en", read_only=True, default=None
    )
    teacher_employee_id = serializers.CharField(
        source="teacher_staff.employee_id", read_only=True, default=None
    )
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
            "teacher_staff",
            "teacher_staff_name",
            "teacher_employee_id",
            "teacher_user",
            "teacher_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _sync_teacher_attrs(
        self, attrs: dict[str, Any], institution_id: Any, instance: Section | None
    ) -> tuple[Staff | None, Any]:
        teacher_staff = (
            attrs.get("teacher_staff")
            if "teacher_staff" in attrs
            else (instance.teacher_staff if instance else None)
        )
        teacher_user = (
            attrs.get("teacher_user")
            if "teacher_user" in attrs
            else (instance.teacher_user if instance else None)
        )

        if "teacher_staff" in attrs:
            if teacher_staff and getattr(teacher_staff, "user", None):
                attrs["teacher_user"] = teacher_staff.user
                teacher_user = teacher_staff.user
            elif teacher_staff is None:
                attrs["teacher_user"] = None
                teacher_user = None
        elif "teacher_user" in attrs:
            if teacher_user:
                stf = Staff.objects.filter(
                    institution_id=institution_id,
                    user=teacher_user,
                    is_deleted=False,
                ).first()
                if stf:
                    attrs["teacher_staff"] = stf
                    teacher_staff = stf
            elif teacher_user is None:
                attrs["teacher_staff"] = None
                teacher_staff = None

        return teacher_staff, teacher_user

    def _validate_conflicts(
        self,
        session: Any,
        instance: Section | None,
        teacher_staff: Staff | None,
        teacher_user: Any,
    ) -> None:
        if teacher_staff and session:
            conflict_staff_qs = Section.objects.filter(
                session=session,
                teacher_staff=teacher_staff,
            )
            if instance:
                conflict_staff_qs = conflict_staff_qs.exclude(pk=instance.pk)
            conflict_staff = conflict_staff_qs.select_related("class_level").first()
            if conflict_staff:
                raise serializers.ValidationError(
                    {
                        "teacher_staff": (
                            f"This teacher is already assigned as Class Teacher for "
                            f"{conflict_staff.class_level.name} - {conflict_staff.name} in this session."
                        )
                    }
                )

        if teacher_user and session:
            conflict_qs = Section.objects.filter(
                session=session,
                teacher_user=teacher_user,
            )
            if instance:
                conflict_qs = conflict_qs.exclude(pk=instance.pk)
            conflict = conflict_qs.select_related("class_level").first()
            if conflict:
                raise serializers.ValidationError(
                    {
                        "teacher_user": (
                            f"This teacher is already assigned as Class Teacher for "
                            f"{conflict.class_level.name} - {conflict.name} in this session."
                        )
                    }
                )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = get_request_institution(self.context["request"])
        instance = self.instance if isinstance(self.instance, Section) else None
        class_level = attrs.get("class_level") or (instance.class_level if instance else None)
        shift = attrs.get("shift") or (instance.shift if instance else None)
        session = attrs.get("session") or (instance.session if instance else None)

        teacher_staff, teacher_user = self._sync_teacher_attrs(attrs, institution.id, instance)

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
        if teacher_staff and teacher_staff.institution_id != institution.id:
            raise serializers.ValidationError(
                {"teacher_staff": "Teacher must belong to your institution."}
            )
        if teacher_user and teacher_user.institution_id != institution.id:
            raise serializers.ValidationError(
                {"teacher_user": "Teacher must belong to your institution."}
            )

        self._validate_conflicts(session, instance, teacher_staff, teacher_user)
        return attrs


class AssignClassTeacherSerializer(serializers.Serializer):
    teacher_staff_id = serializers.UUIDField(required=False, allow_null=True)
    teacher_user_id = serializers.UUIDField(required=False, allow_null=True)


class BulkCreateSectionsSerializer(serializers.Serializer):
    class_id = serializers.UUIDField(required=False, write_only=True)
    class_level_id = serializers.UUIDField(required=False)
    shift_id = serializers.UUIDField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    names = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
        help_text="List of section names (e.g. ['A', 'B', 'C'] or ['Padma', 'Meghna'])",
    )
    capacity = serializers.IntegerField(default=50, min_value=1)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            # Accept class_id as alias for class_level_id
            if "class_id" in data and "class_level_id" not in data:
                data = dict(data)
                data["class_level_id"] = data["class_id"]
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = get_request_institution(self.context["request"])
        class_level_id = attrs.get("class_level_id") or attrs.get("class_id")
        if not class_level_id:
            raise serializers.ValidationError({"class_level_id": "Class level is required."})

        try:
            attrs["class_level"] = ClassLevel.objects.get(
                id=class_level_id, institution=institution
            )
        except ClassLevel.DoesNotExist:
            raise serializers.ValidationError(
                {"class_level_id": "Class level not found in your institution."}
            ) from None

        shift_id = attrs.get("shift_id")
        if shift_id:
            try:
                attrs["shift"] = Shift.objects.get(id=shift_id, institution=institution)
            except Shift.DoesNotExist:
                raise serializers.ValidationError(
                    {"shift_id": "Shift not found in your institution."}
                ) from None
        else:
            shift = Shift.objects.filter(institution=institution).first()
            if not shift:
                shift = Shift.objects.create(
                    institution=institution,
                    name="morning",
                    start_time="07:30:00",
                    end_time="12:00:00",
                )
            attrs["shift"] = shift

        session_id = attrs.get("session_id")
        if session_id:
            try:
                attrs["session"] = AcademicSession.objects.get(
                    id=session_id, institution=institution
                )
            except AcademicSession.DoesNotExist:
                raise serializers.ValidationError(
                    {"session_id": "Academic session not found in your institution."}
                ) from None
        else:
            session = (
                AcademicSession.objects.filter(institution=institution, is_current=True).first()
                or AcademicSession.objects.filter(institution=institution).first()
            )
            if not session:
                import datetime

                year = str(datetime.date.today().year)
                session = AcademicSession.objects.create(
                    institution=institution,
                    name=year,
                    start_date=f"{year}-01-01",
                    end_date=f"{year}-12-31",
                    is_current=True,
                )
            attrs["session"] = session

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

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "name" in data:
                if not data.get("name_en"):
                    data["name_en"] = data["name"]
                if not data.get("name_bn"):
                    data["name_bn"] = data["name"]
            elif data.get("name_en") and not data.get("name_bn"):
                data["name_bn"] = data["name_en"]
            elif data.get("name_bn") and not data.get("name_en"):
                data["name_en"] = data["name_bn"]

            type_val = data.get("subject_type") or data.get("type")
            type_mapping = {
                "theory": SubjectType.COMPULSORY,
                "practical": SubjectType.CO_CURRICULAR,
                "combined": SubjectType.COMPULSORY,
                "optional": SubjectType.OPTIONAL,
                "compulsory": SubjectType.COMPULSORY,
                "fourth_subject": SubjectType.FOURTH_SUBJECT,
                "co_curricular": SubjectType.CO_CURRICULAR,
            }
            if type_val:
                data["type"] = type_mapping.get(str(type_val).lower(), SubjectType.COMPULSORY)
            elif "type" not in data:
                data["type"] = SubjectType.COMPULSORY
        return super().to_internal_value(data)


class ClassSubjectSerializer(serializers.ModelSerializer):
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False, allow_null=True, default=None
    )
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

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "group" not in data:
                data["group"] = None
            if "total_marks" in data and "full_marks" not in data:
                data["full_marks"] = data["total_marks"]
            if "pass_marks" in data and "pass_rule" not in data:
                data["pass_rule"] = {"pass_marks": int(data["pass_marks"])}
            if not data.get("session"):
                request = self.context.get("request")
                if request:
                    institution = get_request_institution(request)
                    sess = (
                        AcademicSession.objects.filter(
                            institution=institution, is_current=True
                        ).first()
                        or AcademicSession.objects.filter(institution=institution).first()
                    )
                    if sess:
                        data["session"] = str(sess.id)
        return super().to_internal_value(data)


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

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "room_number" in data and "name" not in data:
                data["name"] = data["room_number"]
            room_type = data.get("room_type") or data.get("type")
            if room_type:
                type_map = {
                    "classroom": RoomType.CLASSROOM,
                    "lab": RoomType.LAB,
                    "library": RoomType.LIBRARY,
                    "auditorium": RoomType.AUDITORIUM,
                    "other": RoomType.OTHER,
                }
                data["type"] = type_map.get(str(room_type).lower(), RoomType.CLASSROOM)
            elif "type" not in data:
                data["type"] = RoomType.CLASSROOM
            if not data.get("branch"):
                request = self.context.get("request")
                if request:
                    from apps.institutions.models import Branch

                    institution = get_request_institution(request)
                    branch = Branch.objects.filter(institution=institution).first()
                    if branch:
                        data["branch"] = str(branch.id)
        return super().to_internal_value(data)


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

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "period_order" in data and "order" not in data:
                data["order"] = data["period_order"]
            if not data.get("shift"):
                request = self.context.get("request")
                if request:
                    institution = get_request_institution(request)
                    sh = Shift.objects.filter(institution=institution).first()
                    if sh:
                        data["shift"] = str(sh.id)
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance if isinstance(self.instance, Period) else None
        start = attrs.get("start_time") or (instance.start_time if instance else None)
        end = attrs.get("end_time") or (instance.end_time if instance else None)
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class RoutineSlotSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)
    period_number = serializers.IntegerField(source="period.order", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    period_start = serializers.TimeField(source="period.start_time", read_only=True)
    period_end = serializers.TimeField(source="period.end_time", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    subject_name_en = serializers.CharField(source="subject.name_en", read_only=True)
    subject_name_bn = serializers.CharField(source="subject.name_bn", read_only=True, default="")
    day_of_week = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    room_name = serializers.CharField(source="room.name", read_only=True, default=None)
    section_name = serializers.CharField(source="section.name", read_only=True)
    class_level = serializers.UUIDField(source="section.class_level.id", read_only=True)
    class_level_name = serializers.CharField(source="section.class_level.name", read_only=True)
    teacher_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True, default=None
    )
    teacher_staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(), required=False, allow_null=True, default=None
    )
    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(), required=False, allow_null=True, default=None
    )

    def get_day_of_week(self, obj: RoutineSlot) -> int:
        # Django Weekday: 0=Sat, 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri
        # Dart / ISO 8601: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
        mapping = {0: 6, 1: 7, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
        return mapping.get(obj.weekday, 7)

    def get_teacher_name(self, obj: RoutineSlot) -> str | None:
        if obj.teacher_staff:
            return obj.teacher_staff.full_name_en or obj.teacher_staff.full_name_bn
        if obj.teacher_user:
            return obj.teacher_user.full_name or obj.teacher_user.username
        return None

    class Meta:
        model = RoutineSlot
        fields = [
            "id",
            "section",
            "section_name",
            "class_level",
            "class_level_name",
            "weekday",
            "weekday_display",
            "day_of_week",
            "period",
            "period_number",
            "period_name",
            "period_start",
            "period_end",
            "subject",
            "subject_code",
            "subject_name_en",
            "subject_name_bn",
            "teacher_user",
            "teacher_staff",
            "teacher_name",
            "room",
            "room_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            t_input = data.get("teacher_staff") or data.get("teacher_user") or data.get("teacher")
            if t_input is not None and str(t_input).strip() not in ["", "none", "null"]:
                st = Staff.objects.select_related("user").filter(id=t_input).first()
                if st:
                    data["teacher_staff"] = str(st.id)
                    data["teacher_user"] = str(st.user_id) if st.user_id else None
                else:
                    u = User.objects.filter(id=t_input).first()
                    if u:
                        data["teacher_user"] = str(u.id)
                        st_match = Staff.objects.filter(user=u).first()
                        data["teacher_staff"] = str(st_match.id) if st_match else None
                    else:
                        data["teacher_user"] = None
                        data["teacher_staff"] = None
            elif t_input in ["", "none", "null", None] and (
                "teacher_staff" in data
                or "teacher_user" in data
                or "teacher" in data
                or not getattr(self, "partial", False)
            ):
                data["teacher_staff"] = None
                data["teacher_user"] = None

            if "room" in data:
                if str(data.get("room")).strip() in ["", "none", "null", "None"]:
                    data["room"] = None
            elif not getattr(self, "partial", False):
                data["room"] = None

        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = get_request_institution(self.context["request"])
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
        teacher_staff = (
            attrs.get("teacher_staff")
            if "teacher_staff" in attrs
            else (instance.teacher_staff if instance else None)
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
            teacher_staff_id=teacher_staff.id if teacher_staff else None,
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
    section_id = serializers.UUIDField(required=False)
    weekday = serializers.ChoiceField(choices=Weekday.choices)
    period_id = serializers.UUIDField(required=False)
    teacher_user_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    teacher_staff_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    room_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    exclude_slot_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "section" in data and "section_id" not in data:
                data["section_id"] = data["section"]
            if "period" in data and "period_id" not in data:
                data["period_id"] = data["period"]
            if "room" in data and "room_id" not in data:
                data["room_id"] = data["room"]
            if str(data.get("room_id")).strip() in ["", "none", "null", "None"]:
                data["room_id"] = None

            t_val = (
                data.get("teacher_user_id")
                or data.get("teacher_staff_id")
                or data.get("teacher_user")
                or data.get("teacher_staff")
                or data.get("teacher")
            )
            if t_val is not None and str(t_val).strip() not in ["", "none", "null"]:
                st = Staff.objects.select_related("user").filter(id=t_val).first()
                if st:
                    data["teacher_staff_id"] = str(st.id)
                    data["teacher_user_id"] = str(st.user_id) if st.user_id else None
                else:
                    u = User.objects.filter(id=t_val).first()
                    if u:
                        data["teacher_user_id"] = str(u.id)
                        st_match = Staff.objects.filter(user=u).first()
                        data["teacher_staff_id"] = str(st_match.id) if st_match else None
                    else:
                        data["teacher_user_id"] = None
                        data["teacher_staff_id"] = None
            else:
                data["teacher_user_id"] = None
                data["teacher_staff_id"] = None
        return super().to_internal_value(data)
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("section_id"):
            raise serializers.ValidationError({"section_id": "This field is required."})
        if not attrs.get("period_id"):
            raise serializers.ValidationError({"period_id": "This field is required."})
        return attrs


class CopySessionInputSerializer(serializers.Serializer):
    source_session_id = serializers.UUIDField(help_text="UUID of source session to copy from")
    target_session_id = serializers.UUIDField(help_text="UUID of target session to copy into")
    copy_sections = serializers.BooleanField(default=True)
    copy_class_subjects = serializers.BooleanField(default=True)
    copy_routine = serializers.BooleanField(default=False)
    preserve_teachers = serializers.BooleanField(default=False)
    dry_run = serializers.BooleanField(default=True, help_text="True to simulate without saving")


class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    substitute_teacher_name = serializers.SerializerMethodField()
    original_teacher_name = serializers.SerializerMethodField()
    routine_summary = serializers.CharField(source="routine_slot.__str__", read_only=True)
    class_level_name = serializers.CharField(
        source="routine_slot.section.class_level.name", read_only=True, default=None
    )
    section_name = serializers.CharField(
        source="routine_slot.section.name", read_only=True, default=None
    )
    subject_name_en = serializers.CharField(
        source="routine_slot.subject.name_en", read_only=True, default=None
    )
    subject_name_bn = serializers.CharField(
        source="routine_slot.subject.name_bn", read_only=True, default=None
    )
    subject_code = serializers.CharField(
        source="routine_slot.subject.code", read_only=True, default=None
    )
    period_name = serializers.CharField(
        source="routine_slot.period.name", read_only=True, default=None
    )
    period_start = serializers.TimeField(
        source="routine_slot.period.start_time", read_only=True, default=None
    )
    period_end = serializers.TimeField(
        source="routine_slot.period.end_time", read_only=True, default=None
    )
    room_name = serializers.CharField(source="routine_slot.room.name", read_only=True, default=None)
    substitute_teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True, default=None
    )
    substitute_staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(), required=False, allow_null=True, default=None
    )
    original_teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True, default=None
    )
    original_staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(), required=False, allow_null=True, default=None
    )

    class Meta:
        model = SubstituteAssignment
        fields = [
            "id",
            "routine_slot",
            "routine_summary",
            "class_level_name",
            "section_name",
            "subject_name_en",
            "subject_name_bn",
            "subject_code",
            "period_name",
            "period_start",
            "period_end",
            "room_name",
            "slot_date",
            "original_teacher",
            "original_staff",
            "original_teacher_name",
            "substitute_teacher",
            "substitute_staff",
            "substitute_teacher_name",
            "reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_substitute_teacher_name(self, obj: SubstituteAssignment) -> str | None:
        if obj.substitute_staff:
            return obj.substitute_staff.full_name_en or obj.substitute_staff.full_name_bn
        if obj.substitute_teacher:
            return obj.substitute_teacher.full_name or obj.substitute_teacher.username
        return None

    def get_original_teacher_name(self, obj: SubstituteAssignment) -> str | None:
        if obj.original_staff:
            return obj.original_staff.full_name_en or obj.original_staff.full_name_bn
        if obj.original_teacher:
            return obj.original_teacher.full_name or obj.original_teacher.username
        return None

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            # Map 'date' alias to 'slot_date'
            if "date" in data and "slot_date" not in data:
                data["slot_date"] = data["date"]
            # Handle teacher alias
            teacher_val = (
                data.get("teacher")
                or data.get("substitute_teacher_id")
                or data.get("substitute_staff_id")
            )
            if (
                teacher_val
                and not data.get("substitute_staff")
                and not data.get("substitute_teacher")
            ):
                staff_match = Staff.objects.filter(id=teacher_val).first()
                if staff_match:
                    data["substitute_staff"] = str(staff_match.id)
                    if staff_match.user_id:
                        data["substitute_teacher"] = str(staff_match.user_id)
                else:
                    user_match = User.objects.filter(id=teacher_val).first()
                    if user_match:
                        data["substitute_teacher"] = str(user_match.id)
                        if hasattr(user_match, "staff_profile") and user_match.staff_profile:
                            data["substitute_staff"] = str(user_match.staff_profile.id)
            elif data.get("substitute_staff") and not data.get("substitute_teacher"):
                staff_match = Staff.objects.filter(id=data["substitute_staff"]).first()
                if staff_match and staff_match.user_id:
                    data["substitute_teacher"] = str(staff_match.user_id)
        return super().to_internal_value(data)

    def _validate_routine_slot(
        self,
        attrs: dict[str, Any],
        routine_slot: RoutineSlot | None,
        slot_date: Any,
        institution_id: Any,
    ) -> None:
        if not routine_slot:
            return
        if routine_slot.institution_id != institution_id:
            raise serializers.ValidationError(
                {"routine_slot": "Routine slot must belong to your institution."}
            )
        if not attrs.get("original_teacher") and routine_slot.teacher_user:
            attrs["original_teacher"] = routine_slot.teacher_user
        if not attrs.get("original_staff") and routine_slot.teacher_staff:
            attrs["original_staff"] = routine_slot.teacher_staff
        if slot_date:
            expected_weekday = (slot_date.weekday() + 2) % 7
            if routine_slot.weekday != expected_weekday:
                raise serializers.ValidationError(
                    {
                        "slot_date": (
                            f"The selected date ({slot_date}) is a {slot_date.strftime('%A')}, "
                            f"but the routine slot is scheduled for {routine_slot.get_weekday_display()}."
                        )
                    }
                )

    def _validate_teachers(
        self,
        substitute_teacher: Any,
        substitute_staff: Any,
        original_teacher: Any,
        original_staff: Any,
        institution_id: Any,
    ) -> None:
        if not substitute_teacher and not substitute_staff:
            raise serializers.ValidationError(
                {"substitute_staff": "A substitute teacher must be selected."}
            )
        if substitute_teacher and substitute_teacher.institution_id != institution_id:
            raise serializers.ValidationError(
                {"substitute_teacher": "Substitute teacher must belong to your institution."}
            )
        if substitute_staff and substitute_staff.institution_id != institution_id:
            raise serializers.ValidationError(
                {"substitute_staff": "Substitute staff must belong to your institution."}
            )
        if substitute_teacher and original_teacher and substitute_teacher.id == original_teacher.id:
            raise serializers.ValidationError(
                {"substitute_teacher": "Substitute teacher cannot be the original teacher."}
            )
        if substitute_staff and original_staff and substitute_staff.id == original_staff.id:
            raise serializers.ValidationError(
                {"substitute_staff": "Substitute teacher cannot be the original teacher."}
            )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        institution = get_request_institution(self.context["request"])
        instance = self.instance if isinstance(self.instance, SubstituteAssignment) else None
        routine_slot = attrs.get("routine_slot") or (instance.routine_slot if instance else None)
        slot_date = attrs.get("slot_date") or (instance.slot_date if instance else None)

        self._validate_routine_slot(attrs, routine_slot, slot_date, institution.id)

        substitute_teacher = attrs.get("substitute_teacher") or (
            instance.substitute_teacher if instance else None
        )
        substitute_staff = attrs.get("substitute_staff") or (
            instance.substitute_staff if instance else None
        )
        original_teacher = attrs.get("original_teacher") or (
            instance.original_teacher if instance else None
        )
        original_staff = attrs.get("original_staff") or (
            instance.original_staff if instance else None
        )

        self._validate_teachers(
            substitute_teacher,
            substitute_staff,
            original_teacher,
            original_staff,
            institution.id,
        )
        return attrs
