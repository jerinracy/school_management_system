"""DRF serializers for grading scales, subject results, exam summaries, and cumulative standings."""

from rest_framework import serializers

from apps.results.models import (
    CombinedSubjectResult,
    CumulativeResult,
    ExamResult,
    GradeTier,
    GradingScale,
    StudentOptionalSubject,
    SubjectResult,
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

    class Meta:
        model = ExamResult
        fields = [
            "id",
            "exam",
            "student",
            "student_name",
            "student_code",
            "roll_no",
            "section_name",
            "class_level_name",
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
