"""Data models for Homework, Submissions, Syllabus, Lesson Plans, Materials, Online Classes & Quizzes."""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class HomeworkStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    CLOSED = "closed", "Closed"


class SubmissionStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    LATE = "late", "Submitted Late"
    GRADED = "graded", "Graded"
    RETURNED = "returned", "Returned for Revision"


class AVScanStatus(models.TextChoices):
    PENDING = "pending", "Pending Scan"
    CLEAN = "clean", "Clean"
    INFECTED = "infected", "Quarantined / Infected"


class SyllabusStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"


class LessonPlanStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    DELIVERED = "delivered", "Delivered"


class MaterialType(models.TextChoices):
    FILE = "file", "Document / File"
    VIDEO_LINK = "video_link", "Video Link"
    EXTERNAL_LINK = "external_link", "External Reference Link"


class OnlineClassStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    LIVE = "live", "Live Now"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class QuestionType(models.TextChoices):
    MCQ = "mcq", "Multiple Choice (MCQ)"
    TRUE_FALSE = "true_false", "True / False"


class QuizAttemptStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In Progress"
    SUBMITTED = "submitted", "Submitted"
    GRADED = "graded", "Auto-Graded"


class Homework(TenantOwnedModel, SoftDeleteMixin):
    """Homework or assignment issued for a class level / section and subject."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="homework_assignments",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="homework_assignments",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="homework_assignments",
        help_text="Null applies to all sections of the selected class level.",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="homework_assignments",
    )
    teacher = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_homework",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    assigned_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField(db_index=True)
    allow_late_submission = models.BooleanField(default=True)
    late_submission_cutoff_at = models.DateTimeField(null=True, blank=True)
    max_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=HomeworkStatus.choices,
        default=HomeworkStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    due_reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Homework"
        verbose_name_plural = "Homework Assignments"
        ordering = ["-due_at", "-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["institution", "class_level", "section", "status"]),
            models.Index(fields=["institution", "due_at", "status"]),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                check=models.Q(max_marks__gte=Decimal("0.00")),
                name="homework_max_marks_non_negative",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.class_level.name} - {self.subject.name_en})"


class HomeworkAttachment(TenantOwnedModel):
    """Attachment file belonging to a Homework assignment."""

    homework = models.ForeignKey(
        Homework,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="homework/assignments/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    av_scan_status = models.CharField(
        max_length=20,
        choices=AVScanStatus.choices,
        default=AVScanStatus.CLEAN,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Homework Attachment"
        verbose_name_plural = "Homework Attachments"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.original_filename


class HomeworkSubmission(TenantOwnedModel, SoftDeleteMixin):
    """Student submission and teacher evaluation for a Homework assignment."""

    homework = models.ForeignKey(
        Homework,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="homework_submissions",
    )
    text_response = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    is_late = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED,
        db_index=True,
    )
    marks_obtained = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graded_homework_submissions",
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Homework Submission"
        verbose_name_plural = "Homework Submissions"
        ordering = ["-submitted_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["homework", "student"],
                condition=models.Q(is_deleted=False),
                name="unique_active_submission_per_homework_student",
            ),
            models.CheckConstraint(
                check=models.Q(marks_obtained__isnull=True)
                | models.Q(marks_obtained__gte=Decimal("0.00")),
                name="homework_submission_marks_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} -> {self.homework.title} ({self.status})"


class SubmissionAttachment(TenantOwnedModel):
    """Attachment file uploaded by a student inside a HomeworkSubmission."""

    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="homework/submissions/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    av_scan_status = models.CharField(
        max_length=20,
        choices=AVScanStatus.choices,
        default=AVScanStatus.CLEAN,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Submission Attachment"
        verbose_name_plural = "Submission Attachments"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.original_filename


class SyllabusTopic(TenantOwnedModel, SoftDeleteMixin):
    """Curriculum syllabus topic and completion progress per class and subject."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="syllabus_topics",
    )
    term = models.ForeignKey(
        "institutions.Term",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="syllabus_topics",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="syllabus_topics",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="syllabus_topics",
    )
    title = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    estimated_periods = models.PositiveSmallIntegerField(default=2)
    status = models.CharField(
        max_length=20,
        choices=SyllabusStatus.choices,
        default=SyllabusStatus.NOT_STARTED,
        db_index=True,
    )
    completion_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Syllabus Topic"
        verbose_name_plural = "Syllabus Topics"
        ordering = ["class_level", "subject", "order"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                check=models.Q(completion_percentage__gte=0)
                & models.Q(completion_percentage__lte=100),
                name="syllabus_completion_percentage_bounds",
            )
        ]

    def __str__(self) -> str:
        return f"{self.class_level.name} - {self.subject.name_en}: {self.title}"


class LessonPlan(TenantOwnedModel, SoftDeleteMixin):
    """Teacher lesson plan optionally tied to a SyllabusTopic."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="lesson_plans",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="lesson_plans",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="lesson_plans",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="lesson_plans",
    )
    syllabus_topic = models.ForeignKey(
        SyllabusTopic,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lesson_plans",
    )
    teacher = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lesson_plans",
    )
    title = models.CharField(max_length=255)
    lesson_date = models.DateField(db_index=True)
    objectives = models.TextField(blank=True)
    activities = models.TextField(blank=True)
    homework_note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=LessonPlanStatus.choices,
        default=LessonPlanStatus.DRAFT,
        db_index=True,
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Lesson Plan"
        verbose_name_plural = "Lesson Plans"
        ordering = ["-lesson_date", "class_level"]

    def __str__(self) -> str:
        return f"{self.lesson_date} - {self.title}"


class StudyMaterial(TenantOwnedModel, SoftDeleteMixin):
    """Downloadable lecture notes, worksheets, or reference links per class/subject."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="study_materials",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="study_materials",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="study_materials",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="study_materials",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.FILE,
    )
    file = models.FileField(upload_to="homework/materials/%Y/%m/", null=True, blank=True)
    external_url = models.URLField(blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    av_scan_status = models.CharField(
        max_length=20,
        choices=AVScanStatus.choices,
        default=AVScanStatus.CLEAN,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Study Material"
        verbose_name_plural = "Study Materials"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.class_level.name})"


class OnlineClassLink(TenantOwnedModel, SoftDeleteMixin):
    """Scheduled Zoom / Google Meet / virtual class session."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="online_classes",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="online_classes",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="online_classes",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="online_classes",
    )
    teacher = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="online_classes",
    )
    title = models.CharField(max_length=255)
    platform = models.CharField(max_length=30, default="zoom")
    meeting_url = models.URLField()
    meeting_passcode = models.CharField(max_length=64, blank=True)
    scheduled_start = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    status = models.CharField(
        max_length=20,
        choices=OnlineClassStatus.choices,
        default=OnlineClassStatus.SCHEDULED,
        db_index=True,
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Online Class Link"
        verbose_name_plural = "Online Class Links"
        ordering = ["-scheduled_start"]

    def __str__(self) -> str:
        return f"{self.title} ({self.scheduled_start:%Y-%m-%d %H:%M})"


class Quiz(TenantOwnedModel, SoftDeleteMixin):
    """Lightweight online objective quiz for a class / section and subject."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="quizzes",
    )
    teacher = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_quizzes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=20)
    max_attempts = models.PositiveSmallIntegerField(default=1)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    is_published = models.BooleanField(default=False, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"
        ordering = ["-starts_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.class_level.name} - {self.subject.name_en})"


class QuizQuestion(TenantOwnedModel):
    """Question inside an online Quiz."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MCQ,
    )
    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    order = models.PositiveIntegerField(default=1)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Quiz Question"
        verbose_name_plural = "Quiz Questions"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"Q{self.order}: {self.question_text[:60]}"


class QuizOption(TenantOwnedModel):
    """Answer option for a QuizQuestion."""

    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Quiz Option"
        verbose_name_plural = "Quiz Options"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.option_text


class QuizAttempt(TenantOwnedModel):
    """Student attempt and auto-graded score for a Quiz."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    answers_json = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=20,
        choices=QuizAttemptStatus.choices,
        default=QuizAttemptStatus.IN_PROGRESS,
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Quiz Attempt"
        verbose_name_plural = "Quiz Attempts"
        ordering = ["-started_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["quiz", "student", "attempt_number"],
                name="unique_quiz_student_attempt_number",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.quiz.title} (#{self.attempt_number})"
