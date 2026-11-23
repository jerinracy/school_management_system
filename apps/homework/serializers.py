"""DRF Serializers for Homework, Submissions, Syllabus, Lesson Plans, Materials, Online Classes & Quizzes."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.homework.models import (
    Homework,
    HomeworkAttachment,
    HomeworkSubmission,
    LessonPlan,
    OnlineClassLink,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    StudyMaterial,
    SubmissionAttachment,
    SubmissionStatus,
    SyllabusTopic,
)
from apps.homework.permissions import CanManageHomework
from apps.homework.services.storage_service import (
    get_signed_file_download_url,
    validate_and_scan_upload,
)


def _assert_same_institution(context: dict[str, Any], obj: Any, field_name: str) -> None:
    """Prevent cross-tenant foreign key references when request user has an institution."""
    request = context.get("request")
    inst_id = getattr(getattr(request, "user", None), "institution_id", None)
    if inst_id and obj is not None and getattr(obj, "institution_id", None) != inst_id:
        raise serializers.ValidationError(
            {field_name: "Referenced record belongs to another institution."}
        )


class HomeworkAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for homework prompt files with short-lived signed download URLs."""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = HomeworkAttachment
        fields = [
            "id",
            "original_filename",
            "content_type",
            "file_size_bytes",
            "av_scan_status",
            "download_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: HomeworkAttachment) -> str:
        return get_signed_file_download_url(
            obj.file,
            "homework",
            str(obj.id),
            str(obj.institution_id),
            request=self.context.get("request"),
        )


class HomeworkSerializer(serializers.ModelSerializer):
    """Serializer for Homework assignments."""

    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    section_name = serializers.CharField(
        source="section.name", read_only=True, default="All Sections"
    )
    subject_name = serializers.CharField(source="subject.name_en", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name_en", read_only=True, default="")
    attachments = HomeworkAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Homework
        fields = [
            "id",
            "session",
            "class_level",
            "class_level_name",
            "section",
            "section_name",
            "subject",
            "subject_name",
            "teacher",
            "teacher_name",
            "title",
            "description",
            "instructions",
            "assigned_at",
            "due_at",
            "allow_late_submission",
            "late_submission_cutoff_at",
            "max_marks",
            "status",
            "published_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "class_level_name",
            "section_name",
            "subject_name",
            "teacher_name",
            "status",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if hasattr(data, "dict"):
            data = data.dict()
        elif isinstance(data, dict):
            data = dict(data)
            if "due_date" in data and not data.get("due_at"):
                due_val = str(data["due_date"])
                if "T" not in due_val:
                    due_val = f"{due_val}T23:59:59Z"
                data["due_at"] = due_val
            if not data.get("session"):
                request = self.context.get("request")
                if request:
                    from apps.core.mixins import get_request_institution
                    from apps.institutions.models import AcademicSession

                    inst = get_request_institution(request)
                    sess = (
                        AcademicSession.objects.filter(institution=inst, is_current=True).first()
                        or AcademicSession.objects.filter(institution=inst).first()
                    )
                    if sess:
                        data["session"] = str(sess.id)
            if not data.get("teacher"):
                request = self.context.get("request")
                if (
                    request
                    and hasattr(request.user, "staff_profile")
                    and request.user.staff_profile
                ):
                    data["teacher"] = str(request.user.staff_profile.id)
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field_name in ("session", "class_level", "section", "subject", "teacher"):
            _assert_same_institution(self.context, attrs.get(field_name), field_name)
        due_at = attrs.get("due_at", getattr(self.instance, "due_at", None))
        cutoff = attrs.get(
            "late_submission_cutoff_at",
            getattr(self.instance, "late_submission_cutoff_at", None),
        )
        if due_at and cutoff and cutoff < due_at:
            raise serializers.ValidationError(
                {"late_submission_cutoff_at": "Late cutoff cannot be earlier than due date."}
            )
        return attrs


class SubmissionAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for student submission files with signed download URLs."""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionAttachment
        fields = [
            "id",
            "original_filename",
            "content_type",
            "file_size_bytes",
            "av_scan_status",
            "download_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: SubmissionAttachment) -> str:
        return get_signed_file_download_url(
            obj.file,
            "submission",
            str(obj.id),
            str(obj.institution_id),
            request=self.context.get("request"),
        )


class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for student HomeworkSubmissions and teacher evaluation."""

    student_code = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    homework_title = serializers.CharField(source="homework.title", read_only=True)
    attachments = SubmissionAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = HomeworkSubmission
        fields = [
            "id",
            "homework",
            "homework_title",
            "student",
            "student_code",
            "student_name",
            "text_response",
            "submitted_at",
            "is_late",
            "status",
            "marks_obtained",
            "feedback",
            "graded_by",
            "graded_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubmitHomeworkInputSerializer(serializers.Serializer):
    """Input serializer for submitting homework via text and/or uploaded files."""

    text_response = serializers.CharField(required=False, allow_blank=True, default="")
    student = serializers.UUIDField(required=False)


class GradeSubmissionInputSerializer(serializers.Serializer):
    """Input serializer for grading/returning a HomeworkSubmission."""

    marks_obtained = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal("0")
    )
    feedback = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=[
            (SubmissionStatus.GRADED, "Graded"),
            (SubmissionStatus.RETURNED, "Returned for Revision"),
        ],
        default=SubmissionStatus.GRADED,
    )


class SyllabusTopicSerializer(serializers.ModelSerializer):
    """Serializer for curriculum SyllabusTopics."""

    class Meta:
        model = SyllabusTopic
        fields = [
            "id",
            "session",
            "term",
            "class_level",
            "subject",
            "title",
            "title_bn",
            "description",
            "order",
            "estimated_periods",
            "status",
            "completion_percentage",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "completed_at", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field_name in ("session", "term", "class_level", "subject"):
            _assert_same_institution(self.context, attrs.get(field_name), field_name)
        return attrs


class UpdateSyllabusProgressSerializer(serializers.Serializer):
    """Input serializer for updating SyllabusTopic completion percentage."""

    completion_percentage = serializers.IntegerField(min_value=0, max_value=100)


class LessonPlanSerializer(serializers.ModelSerializer):
    """Serializer for teacher LessonPlans."""

    class Meta:
        model = LessonPlan
        fields = [
            "id",
            "session",
            "class_level",
            "section",
            "subject",
            "syllabus_topic",
            "teacher",
            "title",
            "lesson_date",
            "objectives",
            "activities",
            "homework_note",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field_name in (
            "session",
            "class_level",
            "section",
            "subject",
            "syllabus_topic",
            "teacher",
        ):
            _assert_same_institution(self.context, attrs.get(field_name), field_name)
        return attrs


class StudyMaterialSerializer(serializers.ModelSerializer):
    """Serializer for StudyMaterials with validated uploads and signed download URLs."""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = StudyMaterial
        fields = [
            "id",
            "session",
            "class_level",
            "section",
            "subject",
            "title",
            "description",
            "material_type",
            "file",
            "external_url",
            "original_filename",
            "file_size_bytes",
            "av_scan_status",
            "is_published",
            "download_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "file_size_bytes",
            "av_scan_status",
            "download_url",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"file": {"write_only": True, "required": False}}

    def get_download_url(self, obj: StudyMaterial) -> str:
        if not obj.file:
            return obj.external_url or ""
        return get_signed_file_download_url(
            obj.file,
            "material",
            str(obj.id),
            str(obj.institution_id),
            request=self.context.get("request"),
        )

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if hasattr(data, "dict"):
            data = data.dict()
        elif isinstance(data, dict):
            data = dict(data)
            if "class_id" in data and not data.get("class_level"):
                data["class_level"] = data["class_id"]
            if "section_id" in data and not data.get("section"):
                data["section"] = data["section_id"]
            if "subject_id" in data and not data.get("subject"):
                data["subject"] = data["subject_id"]
            if "category" in data and not data.get("material_type"):
                data["material_type"] = "file"
            elif data.get("material_type") not in ("file", "video_link", "external_link"):
                data["material_type"] = "file"
            if not data.get("session"):
                request = self.context.get("request")
                if request:
                    from apps.core.mixins import get_request_institution
                    from apps.institutions.models import AcademicSession

                    inst = get_request_institution(request)
                    sess = (
                        AcademicSession.objects.filter(institution=inst, is_current=True).first()
                        or AcademicSession.objects.filter(institution=inst).first()
                    )
                    if sess:
                        data["session"] = str(sess.id)
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field_name in ("session", "class_level", "section", "subject"):
            _assert_same_institution(self.context, attrs.get(field_name), field_name)
        uploaded_file = attrs.get("file")
        if uploaded_file is not None:
            safe_name, size_bytes, _, av_status = validate_and_scan_upload(uploaded_file)
            attrs["original_filename"] = safe_name
            attrs["file_size_bytes"] = size_bytes
            attrs["av_scan_status"] = av_status
        return attrs


class OnlineClassLinkSerializer(serializers.ModelSerializer):
    """Serializer for Zoom/Google Meet OnlineClassLinks."""

    class Meta:
        model = OnlineClassLink
        fields = [
            "id",
            "session",
            "class_level",
            "section",
            "subject",
            "teacher",
            "title",
            "platform",
            "meeting_url",
            "meeting_passcode",
            "scheduled_start",
            "duration_minutes",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field_name in ("session", "class_level", "section", "subject", "teacher"):
            _assert_same_institution(self.context, attrs.get(field_name), field_name)
        return attrs


class QuizOptionSerializer(serializers.ModelSerializer):
    """Serializer for quiz question options hiding `is_correct` from non-managers."""

    class Meta:
        model = QuizOption
        fields = ["id", "question", "option_text", "is_correct", "order"]
        read_only_fields = ["id"]

    def to_representation(self, instance: QuizOption) -> dict[str, Any]:
        data = super().to_representation(instance)
        request = self.context.get("request")
        view = self.context.get("view")
        if (
            request is not None
            and view is not None
            and not CanManageHomework().has_permission(request, view)
        ):
            data.pop("is_correct", None)
        return data


class QuizQuestionSerializer(serializers.ModelSerializer):
    """Serializer for quiz questions with nested options."""

    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ["id", "quiz", "question_text", "question_type", "marks", "order", "options"]
        read_only_fields = ["id"]


class QuizSerializer(serializers.ModelSerializer):
    """Serializer for lite online Quizzes."""

    questions = QuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "session",
            "class_level",
            "section",
            "subject",
            "teacher",
            "title",
            "description",
            "starts_at",
            "ends_at",
            "duration_minutes",
            "max_attempts",
            "total_marks",
            "pass_marks",
            "is_published",
            "questions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_marks", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field_name in ("session", "class_level", "section", "subject", "teacher"):
            _assert_same_institution(self.context, attrs.get(field_name), field_name)
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError(
                {"ends_at": "Quiz end time must be after start time."}
            )
        return attrs


class QuizAttemptSerializer(serializers.ModelSerializer):
    """Serializer for student QuizAttempts and auto-graded scores."""

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz",
            "student",
            "attempt_number",
            "started_at",
            "submitted_at",
            "answers_json",
            "score",
            "status",
        ]
        read_only_fields = fields


class SubmitQuizAttemptSerializer(serializers.Serializer):
    """Input serializer for submitting answers for an active QuizAttempt."""

    attempt_id = serializers.UUIDField()
    answers = serializers.DictField(child=serializers.CharField())
