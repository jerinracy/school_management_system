"""Models for Results and Grading Engine according to Bangladesh National Curriculum (GPA 5.0)."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class ScaleType(models.TextChoices):
    GPA_5 = "gpa_5", "Bangladesh National Curriculum (GPA 5.0)"
    GPA_4 = "gpa_4", "Standard 4.0 Scale (GPA 4.0)"
    CUSTOM = "custom", "Custom Grading Scale"


class GradingScale(TenantOwnedModel, SoftDeleteMixin):
    """Configurable institutional grading scale (default: BD National Curriculum GPA 5.0)."""

    name = models.CharField(max_length=100, help_text="e.g. BD National Curriculum GPA 5.0")
    scale_type = models.CharField(
        max_length=20,
        choices=ScaleType.choices,
        default=ScaleType.GPA_5,
    )
    max_gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text="Maximum possible grade point average (e.g. 5.00 or 4.00)",
    )
    pass_gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text="Minimum grade point average required to pass (e.g. 1.00)",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this scale is the default for new exams in the institution.",
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Grading Scale"
        verbose_name_plural = "Grading Scales"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_grading_scale_name_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_scale_type_display()})"

    def clean(self) -> None:
        super().clean()
        if self.is_default:
            qs = GradingScale.objects.filter(
                institution=self.institution,
                is_default=True,
                is_deleted=False,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"is_default": "Only one default grading scale is allowed per institution."}
                )


class GradeTier(TenantOwnedModel, SoftDeleteMixin):
    """Specific grade bracket and grade point mapping within a GradingScale."""

    scale = models.ForeignKey(
        GradingScale,
        on_delete=models.CASCADE,
        related_name="tiers",
    )
    letter_grade = models.CharField(
        max_length=10,
        help_text="Letter designation (e.g. A+, A, A-, B, C, D, F)",
    )
    grade_point = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Grade point value (e.g. 5.00, 4.00, 3.50, 3.00, 2.00, 1.00, 0.00)",
    )
    min_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Minimum mark percentage inclusive (e.g. 80.00)",
    )
    max_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Maximum mark percentage inclusive (e.g. 100.00)",
    )
    remarks_en = models.CharField(
        max_length=50, blank=True, help_text="e.g. Outstanding, Excellent"
    )
    remarks_bn = models.CharField(max_length=50, blank=True, help_text="e.g. অসাধারণ, চমৎকার")

    class Meta:
        ordering = ["-grade_point", "-min_percentage"]
        verbose_name = "Grade Tier"
        verbose_name_plural = "Grade Tiers"
        constraints = [
            models.UniqueConstraint(
                fields=["scale", "letter_grade"],
                condition=models.Q(is_deleted=False),
                name="unique_letter_grade_per_scale",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.letter_grade} ({self.grade_point}) [{self.min_percentage}% - {self.max_percentage}%]"


class StudentOptionalSubject(TenantOwnedModel, SoftDeleteMixin):
    """Designation of a 4th / optional subject for a student in a session and class."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="optional_subject_assignments",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="optional_subject_assignments",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="optional_subject_assignments",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="optional_student_assignments",
    )

    class Meta:
        verbose_name = "Student 4th/Optional Subject"
        verbose_name_plural = "Student 4th/Optional Subjects"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student", "session"],
                condition=models.Q(is_deleted=False),
                name="unique_optional_subject_per_student_session",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - 4th Subject: {self.subject.name_en}"


class SubjectResult(TenantOwnedModel, SoftDeleteMixin):
    """Calculated academic result for a student in a specific ExamSubject."""

    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    exam_subject = models.ForeignKey(
        "exams.ExamSubject",
        on_delete=models.CASCADE,
        related_name="results",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="subject_results",
    )
    creative_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    mcq_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    practical_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    full_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )
    marks_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    grade_point = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    letter_grade = models.CharField(
        max_length=10,
        default="F",
    )
    is_passed = models.BooleanField(
        default=False,
    )
    is_absent = models.BooleanField(
        default=False,
    )
    grace_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    is_fourth_subject = models.BooleanField(
        default=False,
    )
    fail_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Detailed failure reason e.g. 'MCQ component failed (8 < 10)'",
    )

    class Meta:
        verbose_name = "Subject Result"
        verbose_name_plural = "Subject Results"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "exam_subject", "student"],
                condition=models.Q(is_deleted=False),
                name="unique_subject_result_per_exam_subject_student",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "exam", "student"]),
            models.Index(fields=["exam_subject", "is_passed"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.exam_subject.subject.name_en}: {self.letter_grade} ({self.grade_point})"


class CombinedSubjectResult(TenantOwnedModel, SoftDeleteMixin):
    """Combined 1st & 2nd paper result (e.g. Bangla 1st + 2nd, English 1st + 2nd) evaluated across 200 marks."""

    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="combined_results",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="combined_results",
    )
    paper_1 = models.ForeignKey(
        "exams.ExamSubject",
        on_delete=models.CASCADE,
        related_name="+",
    )
    paper_2 = models.ForeignKey(
        "exams.ExamSubject",
        on_delete=models.CASCADE,
        related_name="+",
    )
    combined_name = models.CharField(
        max_length=100,
        help_text="e.g. Bangla (Combined), English (Combined)",
    )
    paper_1_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    paper_2_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    full_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("200.00"),
    )
    marks_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    grade_point = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    letter_grade = models.CharField(
        max_length=10,
        default="F",
    )
    is_passed = models.BooleanField(
        default=False,
    )
    fail_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        verbose_name = "Combined Subject Result"
        verbose_name_plural = "Combined Subject Results"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "exam", "student", "paper_1"],
                condition=models.Q(is_deleted=False),
                name="unique_combined_result_per_student_paper1",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.combined_name}: {self.letter_grade} ({self.grade_point})"


class ExamResultStatus(models.TextChoices):
    DRAFT = "draft", "Draft (Tabulating)"
    APPROVED = "approved", "Approved by Head Teacher"
    PUBLISHED = "published", "Published to Students/Guardians"


class ExamResult(TenantOwnedModel, SoftDeleteMixin):
    """Aggregate result summary for a student across all subjects in an examination."""

    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="results",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="exam_results",
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        on_delete=models.CASCADE,
        related_name="exam_results",
    )
    total_marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_full_marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    gpa_without_fourth = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="GPA calculated solely across mandatory subjects.",
    )
    fourth_subject_bonus = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Bonus grade points from 4th subject above 2.00 (max 3.00 points).",
    )
    final_gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Final GPA including 4th subject bonus, capped at 5.00 (0.00 if failed any mandatory).",
    )
    final_grade = models.CharField(
        max_length=10,
        default="F",
        help_text="Letter grade matching the final GPA.",
    )
    is_passed = models.BooleanField(
        default=False,
        help_text="True if student passed all compulsory subjects.",
    )
    failed_subject_count = models.PositiveIntegerField(
        default=0,
    )
    failed_subjects_summary = models.JSONField(
        default=list,
        blank=True,
        help_text="List of names of subjects failed.",
    )
    section_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Merit rank within the section.",
    )
    class_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Merit rank within the entire class level.",
    )
    status = models.CharField(
        max_length=20,
        choices=ExamResultStatus.choices,
        default=ExamResultStatus.DRAFT,
    )
    calculated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["class_position", "section_position", "-final_gpa", "-total_marks"]
        verbose_name = "Exam Result"
        verbose_name_plural = "Exam Results"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "exam", "student"],
                condition=models.Q(is_deleted=False),
                name="unique_exam_result_per_student",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "exam", "class_position"]),
            models.Index(fields=["institution", "exam", "section_position"]),
            models.Index(fields=["exam", "is_passed"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.exam.name}: GPA {self.final_gpa} ({self.final_grade})"


class TermWeightageRule(TenantOwnedModel, SoftDeleteMixin):
    """Weightage percentage assigned to an exam for annual/cumulative grade calculation."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="term_weightages",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="term_weightages",
    )
    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="weightage_rules",
    )
    weightage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage contribution towards cumulative annual result (e.g. 30.00, 70.00).",
    )

    class Meta:
        verbose_name = "Term Weightage Rule"
        verbose_name_plural = "Term Weightage Rules"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "session", "class_level", "exam"],
                condition=models.Q(is_deleted=False),
                name="unique_weightage_rule_per_exam_class_session",
            )
        ]

    def __str__(self) -> str:
        return f"{self.class_level.name} - {self.exam.name}: {self.weightage_percentage}%"


class CumulativeResult(TenantOwnedModel, SoftDeleteMixin):
    """Annual session cumulative performance across all weighted exams."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="cumulative_results",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="cumulative_results",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="cumulative_results",
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        on_delete=models.CASCADE,
        related_name="cumulative_results",
    )
    term_results = models.JSONField(
        default=list,
        blank=True,
        help_text="Detailed array of term exams, weights, marks obtained, and GPAs.",
    )
    cumulative_marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    cumulative_gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    cumulative_grade = models.CharField(
        max_length=10,
        default="F",
    )
    is_passed = models.BooleanField(
        default=False,
    )
    final_section_position = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    final_class_position = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    promotion_recommended = models.BooleanField(
        default=False,
        help_text="Whether this student meets institutional criteria for promotion to next class level.",
    )
    calculated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["final_class_position", "final_section_position", "-cumulative_gpa"]
        verbose_name = "Cumulative Annual Result"
        verbose_name_plural = "Cumulative Annual Results"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "session", "class_level", "student"],
                condition=models.Q(is_deleted=False),
                name="unique_cumulative_result_per_student_session",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - Annual CGPA {self.cumulative_gpa} ({self.cumulative_grade})"


class TabulationSheetFormat(models.TextChoices):
    EXCEL = "xlsx", "Excel Spreadsheet (.xlsx)"
    PDF = "pdf", "PDF Document (.pdf)"


class TabulationSheet(TenantOwnedModel, SoftDeleteMixin):
    """Archived and downloadable examination tabulation broadsheet for a class/section."""

    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="tabulation_sheets",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="tabulation_sheets",
    )
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tabulation_sheets",
        help_text="Optional section filter. If blank, includes all sections of the class level.",
    )
    file_format = models.CharField(
        max_length=10,
        choices=TabulationSheetFormat.choices,
        default=TabulationSheetFormat.EXCEL,
    )
    file = models.FileField(
        upload_to="results/tabulations/%Y/%m/",
        blank=True,
        null=True,
    )
    version = models.PositiveIntegerField(
        default=1,
    )
    generated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
    )
    total_students = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "Tabulation Sheet"
        verbose_name_plural = "Tabulation Sheets"
        indexes = [
            models.Index(fields=["institution", "exam", "class_level"]),
        ]

    def __str__(self) -> str:
        sec_str = f" - {self.section.name}" if self.section else " (All Sections)"
        return f"{self.exam.name} - {self.class_level.name}{sec_str} ({self.file_format.upper()} v{self.version})"


class ReportCardTemplateStyle(models.TextChoices):
    DEFAULT_BD = "default_bd", "Standard Bangladesh National Curriculum"
    MODERN = "modern", "Modern Bilingual Card"


class ReportCard(TenantOwnedModel, SoftDeleteMixin):
    """Official student progress report card document."""

    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="report_cards",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="report_cards",
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        on_delete=models.CASCADE,
        related_name="report_cards",
    )
    exam_result = models.ForeignKey(
        "results.ExamResult",
        on_delete=models.CASCADE,
        related_name="report_cards",
        null=True,
        blank=True,
    )
    template_style = models.CharField(
        max_length=20,
        choices=ReportCardTemplateStyle.choices,
        default=ReportCardTemplateStyle.DEFAULT_BD,
    )
    file = models.FileField(
        upload_to="results/report_cards/%Y/%m/",
        blank=True,
        null=True,
    )
    generated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "Report Card"
        verbose_name_plural = "Report Cards"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "exam", "student"],
                condition=models.Q(is_deleted=False),
                name="unique_report_card_per_exam_student",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "exam", "student"]),
        ]

    def __str__(self) -> str:
        return f"Report Card: {self.student.student_id} - {self.exam.name}"


class ResultPublication(TenantOwnedModel, SoftDeleteMixin):
    """Institutional publication control and visibility schedule for examination results."""

    exam = models.OneToOneField(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="publication",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="If True, results are officially published and visible to authorized users.",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    is_visible_to_guardians = models.BooleanField(
        default=True,
        help_text="Allow guardians to view this exam's results on the portal/app.",
    )
    is_visible_to_students = models.BooleanField(
        default=True,
        help_text="Allow students to view their own result on the portal/app.",
    )
    allow_public_search = models.BooleanField(
        default=False,
        help_text="Allow public unauthenticated result lookup via student ID/roll number.",
    )
    published_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    remarks = models.TextField(
        blank=True,
        help_text="Official remarks or publication notes from the Head Teacher/Principal.",
    )

    class Meta:
        verbose_name = "Result Publication"
        verbose_name_plural = "Result Publications"

    def __str__(self) -> str:
        status_str = "Published" if self.is_published else "Draft/Unpublished"
        return f"{self.exam.name} - {status_str}"
