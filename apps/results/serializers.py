"""DRF serializers for grading scales, subject results, exam summaries, and cumulative standings."""

from rest_framework import serializers

from apps.results.models import (
    CombinedSubjectResult,
    CumulativeResult,
    ExamResult,
    GradeTier,
    GradingScale,
    ReportCard,
    ResultPublication,
    StudentOptionalSubject,
    SubjectResult,
    TabulationSheet,
    TermWeightageRule,
)


class GradeTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeTier
        fields = [
            "id",
            "letter_grade",
            "grade_point",
            "min_percentage",
            "max_percentage",
            "remarks_en",
            "remarks_bn",
        ]


class GradingScaleSerializer(serializers.ModelSerializer):
    tiers = GradeTierSerializer(many=True, read_only=True)

    class Meta:
        model = GradingScale
        fields = [
            "id",
            "name",
            "scale_type",
            "max_gpa",
            "pass_gpa",
            "is_default",
            "description",
            "tiers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentOptionalSubjectSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    subject_name = serializers.CharField(source="subject.name_en", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = StudentOptionalSubject
        fields = [
            "id",
            "student",
            "student_name",
            "student_code",
            "session",
            "class_level",
            "subject",
            "subject_name",
            "subject_code",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SubjectResultSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="exam_subject.subject.name_en", read_only=True)
    subject_code = serializers.CharField(source="exam_subject.subject.code", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)

    class Meta:
        model = SubjectResult
        fields = [
            "id",
            "exam",
            "exam_subject",
            "subject_name",
            "subject_code",
            "student",
            "student_name",
            "student_code",
            "creative_marks",
            "mcq_marks",
            "practical_marks",
            "total_marks",
            "full_marks",
            "marks_percentage",
            "grade_point",
            "letter_grade",
            "is_passed",
            "is_absent",
            "grace_marks",
            "is_fourth_subject",
            "fail_reason",
        ]
        read_only_fields = fields


class CombinedSubjectResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)

    class Meta:
        model = CombinedSubjectResult
        fields = [
            "id",
            "exam",
            "student",
            "student_name",
            "paper_1",
            "paper_2",
            "combined_name",
            "paper_1_marks",
            "paper_2_marks",
            "total_marks",
            "full_marks",
            "marks_percentage",
            "grade_point",
            "letter_grade",
            "is_passed",
            "fail_reason",
        ]
        read_only_fields = fields


class ExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    roll_no = serializers.IntegerField(source="enrollment.roll_no", read_only=True)
    section_name = serializers.CharField(source="enrollment.section.name", read_only=True)
    class_level_name = serializers.CharField(source="enrollment.class_level.name", read_only=True)
    class_level = serializers.UUIDField(source="enrollment.class_level_id", read_only=True)
    section = serializers.UUIDField(source="enrollment.section_id", read_only=True)

    class Meta:
        model = ExamResult
        fields = [
            "id",
            "exam",
            "student",
            "student_name",
            "student_code",
            "roll_no",
            "class_level",
            "class_level_name",
            "section",
            "section_name",
            "total_marks",
            "total_full_marks",
            "percentage",
            "gpa_without_fourth",
            "fourth_subject_bonus",
            "final_gpa",
            "final_grade",
            "is_passed",
            "failed_subject_count",
            "failed_subjects_summary",
            "section_position",
            "class_position",
            "status",
            "calculated_at",
        ]
        read_only_fields = fields


class ExamResultCalculateSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=True)
    async_mode = serializers.BooleanField(default=False)


class ExamSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    passed_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    pass_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    gpa_5_count = serializers.IntegerField()
    gpa_distribution = serializers.DictField()


class TermWeightageRuleSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)

    class Meta:
        model = TermWeightageRule
        fields = [
            "id",
            "session",
            "class_level",
            "class_level_name",
            "exam",
            "exam_name",
            "weightage_percentage",
        ]


class CumulativeResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    roll_no = serializers.IntegerField(source="enrollment.roll_no", read_only=True)
    section_name = serializers.CharField(source="enrollment.section.name", read_only=True)

    class Meta:
        model = CumulativeResult
        fields = [
            "id",
            "session",
            "class_level",
            "student",
            "student_name",
            "student_code",
            "roll_no",
            "section_name",
            "term_results",
            "cumulative_marks",
            "cumulative_gpa",
            "cumulative_grade",
            "is_passed",
            "final_section_position",
            "final_class_position",
            "promotion_recommended",
            "calculated_at",
        ]
        read_only_fields = fields


class CumulativeCalculateSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    class_level_id = serializers.UUIDField(required=True)
    async_mode = serializers.BooleanField(default=False)


class TabulationSheetSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    class_level_name = serializers.CharField(source="class_level.name", read_only=True)
    section_name = serializers.CharField(
        source="section.name", read_only=True, default="All Sections"
    )
    download_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = TabulationSheet
        fields = [
            "id",
            "exam",
            "exam_name",
            "class_level",
            "class_level_name",
            "section",
            "section_name",
            "file_format",
            "file",
            "download_url",
            "version",
            "total_students",
            "generated_at",
        ]
        read_only_fields = [
            "id",
            "download_url",
            "version",
            "total_students",
            "generated_at",
        ]


class TabulationGenerateSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=True)
    class_level_id = serializers.UUIDField(required=True)
    section_id = serializers.UUIDField(required=False, allow_null=True)
    file_format = serializers.ChoiceField(choices=["xlsx", "pdf"], default="xlsx")
    async_mode = serializers.BooleanField(default=False)


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    roll_no = serializers.IntegerField(source="enrollment.roll_no", read_only=True)
    class_level_name = serializers.CharField(source="enrollment.class_level.name", read_only=True)
    section_name = serializers.CharField(source="enrollment.section.name", read_only=True)
    download_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = ReportCard
        fields = [
            "id",
            "exam",
            "exam_name",
            "student",
            "student_name",
            "student_code",
            "roll_no",
            "class_level_name",
            "section_name",
            "template_style",
            "file",
            "download_url",
            "generated_at",
        ]
        read_only_fields = ["id", "download_url", "generated_at"]


class ReportCardGenerateSerializer(serializers.Serializer):
    exam_result_id = serializers.UUIDField(required=True)
    template_style = serializers.ChoiceField(choices=["default_bd", "modern"], default="default_bd")


class ReportCardBulkZipSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=True)
    class_level_id = serializers.UUIDField(required=True)
    section_id = serializers.UUIDField(required=False, allow_null=True)
    async_mode = serializers.BooleanField(default=False)


class ResultPublicationSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = ResultPublication
        fields = [
            "id",
            "exam",
            "exam_name",
            "is_published",
            "published_at",
            "is_visible_to_guardians",
            "is_visible_to_students",
            "allow_public_search",
            "remarks",
        ]
        read_only_fields = ["id", "published_at"]


class ResultApproveSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=True)


class ResultPublishSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=True)
    is_visible_to_guardians = serializers.BooleanField(default=True)
    is_visible_to_students = serializers.BooleanField(default=True)
    allow_public_search = serializers.BooleanField(default=False)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PublicResultSearchSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=True)
    student_id = serializers.CharField(required=False, allow_blank=True)
    roll_no = serializers.IntegerField(required=False, allow_null=True)


class WeakStudentsResponseSerializer(serializers.Serializer):
    exam_id = serializers.CharField()
    exam_name = serializers.CharField()
    total_students = serializers.IntegerField()
    weak_student_count = serializers.IntegerField()
    weak_student_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    subject_failure_frequencies = serializers.ListField(child=serializers.DictField())
    students = serializers.ListField(child=serializers.DictField())


class PromotionEligibilityResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    class_level_id = serializers.CharField()
    criteria = serializers.DictField()
    counts = serializers.DictField()
    eligible = serializers.ListField(child=serializers.DictField())
    conditional = serializers.ListField(child=serializers.DictField())
    retained = serializers.ListField(child=serializers.DictField())
