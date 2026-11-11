"""Data models for examinations, scheduling, admit cards, and mark entries."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.academics.models import ClassLevel, Section, Subject
from apps.core.models import TenantOwnedModel
from apps.institutions.models import AcademicSession


class ExamStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    IN_PROGRESS = "in_progress", "In Progress"
    MARKING = "marking", "Marking"
    LOCKED = "locked", "Locked"
    PUBLISHED = "published", "Published"


class ClearanceStatus(models.TextChoices):
    ELIGIBLE = "eligible", "Regular Eligible"
    NON_COLLEGIATE = "non_collegiate", "Non-Collegiate (Attendance 60-74%)"
    DISQUALIFIED = "disqualified", "Disqualified (Attendance <60% or Dues)"
    CLEARED_BY_PRINCIPAL = "cleared_by_principal", "Cleared by Special Permission"


class ReScrutinyStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    REVIEWED = "reviewed", "Reviewed (No Change)"
    APPROVED = "approved", "Approved (Marks Changed)"
    REJECTED = "rejected", "Rejected"


class ExamType(TenantOwnedModel):
    """Institutional classification of examinations (e.g. Class Test, Final, Model Test)."""

    name = models.CharField(max_length=100, help_text="Exam type name (e.g. Half-Yearly, Annual)")
    code = models.CharField(
        max_length=50, help_text="Unique code per institution (e.g. HY, ANNUAL)"
    )
    is_board_exam = models.BooleanField(
        default=False,
        help_text="Whether this simulates or maps to a national board exam (SSC/HSC/JSC)",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Exam Type"
        verbose_name_plural = "Exam Types"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_exam_type_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Exam(TenantOwnedModel):
    """Concrete examination event bound to an academic session and target classes."""

    exam_type = models.ForeignKey(
        ExamType,
        on_delete=models.PROTECT,
        related_name="exams",
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="exams",
    )
    name = models.CharField(
        max_length=150, help_text="Full exam title (e.g. Annual Examination 2026)"
    )
    term = models.CharField(max_length=50, blank=True, help_text="Term or Semester name")
    start_date = models.DateField()
    end_date = models.DateField()
    weightage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text="Percentage weightage contributing to final annual evaluation (0-100%)",
    )
    status = models.CharField(
        max_length=20,
        choices=ExamStatus.choices,
        default=ExamStatus.DRAFT,
        db_index=True,
    )
    target_classes = models.ManyToManyField(
        ClassLevel,
        blank=True,
        related_name="exams",
        help_text="Class levels participating in this exam",
    )
    publish_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date", "name"]
        verbose_name = "Examination"
        verbose_name_plural = "Examinations"

    def __str__(self) -> str:
        return f"{self.name} - {self.session.name} ({self.status})"

    def clean(self) -> None:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Exam start date cannot be later than end date.")


class ExamSubject(TenantOwnedModel):
    """Subject-specific paper configuration within an examination."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="exam_subjects",
    )
    class_level = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        related_name="exam_subjects",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="exam_subjects",
    )
    exam_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    room = models.CharField(max_length=100, blank=True)

    # Component Marks Breakdown
    full_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("100.00"))
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("33.00"))

    creative_full_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("70.00"),
        help_text="Creative / Written (CQ) max marks",
    )
    creative_pass_marks = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("23.00")
    )

    mcq_full_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("30.00"),
        help_text="Multiple Choice (MCQ) max marks",
    )
    mcq_pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("10.00"))

    practical_full_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Practical exam max marks (if applicable)",
    )
    practical_pass_marks = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00")
    )

    # Combined Paper rule (Bangla 1st + 2nd, English 1st + 2nd)
    is_combined_paper = models.BooleanField(
        default=False,
        help_text="True if this subject is evaluated jointly with another paper",
    )
    combined_with = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="paired_papers",
        help_text="Paired subject paper for combined pass determination",
    )

    assigned_teacher = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_exam_subjects",
        help_text="Staff/Teacher authorized to enter and review marks",
    )
    is_marks_locked = models.BooleanField(
        default=False,
        help_text="Locked once entry closes; requires admin authorization to unlock",
    )

    class Meta:
        ordering = ["exam_date", "start_time", "subject__name_en"]
        verbose_name = "Exam Subject"
        verbose_name_plural = "Exam Subjects"
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "class_level", "subject"],
                name="unique_exam_class_subject",
            )
        ]

    def __str__(self) -> str:
        return f"{self.exam.name} - {self.class_level.name} - {self.subject.name_en}"

    def clean(self) -> None:
        total_components = (
            self.creative_full_marks + self.mcq_full_marks + self.practical_full_marks
        )
        if total_components != self.full_marks:
            raise ValidationError(
                f"Sum of component marks ({total_components}) must equal full marks ({self.full_marks})."
            )


class ExamRoutine(TenantOwnedModel):
    """Timetable mapping date, time slot, and venue for each exam subject."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="routines",
    )
    exam_subject = models.ForeignKey(
        ExamSubject,
        on_delete=models.CASCADE,
        related_name="routines",
    )
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=50, blank=True)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["exam_date", "start_time"]
        verbose_name = "Exam Routine"
        verbose_name_plural = "Exam Routines"

    def __str__(self) -> str:
        return f"{self.exam.name}: {self.exam_subject.subject.name_en} ({self.exam_date} {self.start_time})"


class ExamEligibilityPolicy(TenantOwnedModel):
    """Configurable attendance and financial thresholds required to sit for an exam."""

    exam = models.OneToOneField(
        Exam,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="eligibility_policy",
        help_text="If null, represents institution-wide default exam eligibility policy",
    )
    min_attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("75.00"),
        help_text="Standard attendance percentage for regular eligibility (default 75%)",
    )
    non_collegiate_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("60.00"),
        help_text="Minimum attendance percentage for non-collegiate consideration (default 60%)",
    )
    allow_non_collegiate = models.BooleanField(
        default=True,
        help_text="Allow students with 60-74% attendance with penalty fee or principal approval",
    )
    require_fee_clearance = models.BooleanField(
        default=True,
        help_text="Require clearance of tuition/exam fees before issuing admit cards",
    )

    class Meta:
        verbose_name = "Exam Eligibility Policy"
        verbose_name_plural = "Exam Eligibility Policies"

    def __str__(self) -> str:
        target = self.exam.name if self.exam else "Default Institutional Policy"
        return f"Eligibility Policy: {target} (Min: {self.min_attendance_percentage}%)"


class StudentExamEligibility(TenantOwnedModel):
    """Calculated student eligibility record based on attendance and fee clearance."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="student_eligibilities",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="exam_eligibilities",
    )
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    dues_cleared = models.BooleanField(default=True)
    clearance_status = models.CharField(
        max_length=30,
        choices=ClearanceStatus.choices,
        default=ClearanceStatus.ELIGIBLE,
        db_index=True,
    )
    clearance_notes = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student__student_id"]
        verbose_name = "Student Exam Eligibility"
        verbose_name_plural = "Student Exam Eligibilities"
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student"],
                name="unique_exam_student_eligibility",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.exam.name}: {self.clearance_status}"


class SeatPlan(TenantOwnedModel):
    """Physical examination seating arrangement per room and bench."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="seat_plans",
    )
    exam_subject = models.ForeignKey(
        ExamSubject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="seat_plans",
    )
    room_number = models.CharField(max_length=50)
    bench_label = models.CharField(max_length=50, help_text="Bench identifier e.g. R1-B1")
    seat_number = models.PositiveIntegerField(default=1)
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="seat_allocations",
    )
    roll_number = models.PositiveIntegerField(default=1)
    class_level = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        related_name="seat_plans",
    )
    section = models.ForeignKey(
        Section,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="seat_plans",
    )

    class Meta:
        ordering = ["room_number", "bench_label", "seat_number"]
        verbose_name = "Seat Plan"
        verbose_name_plural = "Seat Plans"

    def __str__(self) -> str:
        return f"Room {self.room_number}, Bench {self.bench_label} - Roll {self.roll_number} ({self.student.name_en})"


class AdmitCard(TenantOwnedModel):
    """Printable examination permit tracking card issuance and verification."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="admit_cards",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="admit_cards",
    )
    card_number = models.CharField(max_length=60, db_index=True)
    issue_date = models.DateField(default=timezone.localdate)
    is_issued = models.BooleanField(default=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["card_number"]
        verbose_name = "Admit Card"
        verbose_name_plural = "Admit Cards"
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student"],
                name="unique_exam_student_admit_card",
            ),
            models.UniqueConstraint(
                fields=["institution", "card_number"],
                name="unique_admit_card_no_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"Admit Card {self.card_number}: {self.student.name_en} ({self.exam.name})"


class MarkEntry(TenantOwnedModel):
    """Raw component mark entry per student and examination subject."""

    exam_subject = models.ForeignKey(
        ExamSubject,
        on_delete=models.CASCADE,
        related_name="marks",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="marks",
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
        null=True,
        blank=True,
    )
    is_absent = models.BooleanField(
        default=False,
        help_text="Flagged when student was absent during examination",
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked to prevent further modifications without administrative unlock",
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="entered_marks",
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="locked_marks",
    )

    class Meta:
        ordering = ["student__student_id"]
        verbose_name = "Mark Entry"
        verbose_name_plural = "Mark Entries"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_subject", "student"],
                name="unique_exam_subject_student_mark",
            )
        ]

    def __str__(self) -> str:
        status = "ABSENT" if self.is_absent else f"Total: {self.total_marks}"
        return f"{self.student.student_id} - {self.exam_subject.subject.name_en}: {status}"

    def calculate_total(self) -> Decimal:
        """Sum present components."""
        if self.is_absent:
            return Decimal("0.00")
        total = Decimal("0.00")
        if self.creative_marks is not None:
            total += self.creative_marks
        if self.mcq_marks is not None:
            total += self.mcq_marks
        if self.practical_marks is not None:
            total += self.practical_marks
        return total


class MarkEntryLog(TenantOwnedModel):
    """Audit log tracking every modification to examination mark records."""

    mark_entry = models.ForeignKey(
        MarkEntry,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    field_name = models.CharField(max_length=50)
    old_value = models.CharField(max_length=50, null=True, blank=True)
    new_value = models.CharField(max_length=50, null=True, blank=True)
    reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Mark Entry Log"
        verbose_name_plural = "Mark Entry Logs"

    def __str__(self) -> str:
        return f"Log {self.mark_entry_id}: {self.field_name} changed ({self.old_value} -> {self.new_value})"


class GraceMarkRule(TenantOwnedModel):
    """Institutional rules for awarding grace marks to borderline passing students."""

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="grace_mark_rules",
    )
    subject = models.ForeignKey(
        Subject,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="If null, applies across all subjects for this exam",
    )
    max_grace_marks = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("2.00"),
        help_text="Maximum allowable grace mark addition (e.g. 2 to 5 marks)",
    )
    condition_desc = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Grace Mark Rule"
        verbose_name_plural = "Grace Mark Rules"

    def __str__(self) -> str:
        subj = self.subject.name_en if self.subject else "All Subjects"
        return f"Grace Rule ({self.exam.name} - {subj}): Max +{self.max_grace_marks}"


class ReScrutinyRequest(TenantOwnedModel):
    """Formal student/guardian request for re-checking and scrutinizing subject marks."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="rescrutiny_requests",
    )
    exam_subject = models.ForeignKey(
        ExamSubject,
        on_delete=models.CASCADE,
        related_name="rescrutiny_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requested_rescrutinies",
    )
    previous_creative_marks = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    previous_mcq_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    previous_practical_marks = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    revised_creative_marks = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    revised_mcq_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    revised_practical_marks = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=ReScrutinyStatus.choices,
        default=ReScrutinyStatus.PENDING,
        db_index=True,
    )
    fee_paid = models.BooleanField(default=False)
    reviewer_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Re-Scrutiny Request"
        verbose_name_plural = "Re-Scrutiny Requests"

    def __str__(self) -> str:
        return f"ReScrutiny: {self.student.student_id} - {self.exam_subject.subject.name_en} ({self.status})"
