"""Admission models for School Management System."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantOwnedModel


class CircularStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    CLOSED = "closed", "Closed"


class ApplicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    PAID = "paid", "Application Fee Paid"
    SHORTLISTED = "shortlisted", "Shortlisted"
    TEST_SCHEDULED = "test_scheduled", "Admission Test Scheduled"
    ADMITTED = "admitted", "Admitted"
    WAITLISTED = "waitlisted", "Waitlisted"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class GenderChoices(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class ReligionChoices(models.TextChoices):
    ISLAM = "islam", "Islam"
    HINDUISM = "hinduism", "Hinduism"
    BUDDHISM = "buddhism", "Buddhism"
    CHRISTIANITY = "christianity", "Christianity"
    OTHER = "other", "Other"


class BloodGroupChoices(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    UNKNOWN = "unknown", "Unknown"


class QuotaType(models.TextChoices):
    GENERAL = "general", "General Merit"
    SIBLING = "sibling", "Sibling of Current Student"
    STAFF_CHILD = "staff_child", "Child of School Staff / Teacher"
    FREEDOM_FIGHTER = "freedom_fighter", "Freedom Fighter Quota (Muktidjoddha)"
    DISABILITY = "disability", "Special Needs / Disability"
    CATCHMENT = "catchment", "Catchment / Local Area Quota"


class PaymentMethod(models.TextChoices):
    BKASH = "bkash", "bKash"
    NAGAD = "nagad", "Nagad"
    ROCKET = "rocket", "Rocket"
    BANK = "bank", "Bank Transfer"
    CASH = "cash", "Cash at School Counter"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class MeritType(models.TextChoices):
    MERIT = "merit", "Selected (Merit)"
    WAITING = "waiting", "Waiting List"
    QUOTA = "quota", "Selected (Quota)"


class AdmissionCircular(TenantOwnedModel):
    """Admission intake circular for a class level and session."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="admission_circulars",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        on_delete=models.CASCADE,
        related_name="admission_circulars",
    )
    title = models.CharField(max_length=255, help_text="e.g. Admission Circular 2026 - Class 6")
    seats_available = models.PositiveIntegerField(default=50)
    application_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Fee required to confirm application submission",
    )
    form_open_date = models.DateField()
    form_close_date = models.DateField()
    instructions = models.TextField(blank=True)
    eligibility_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="e.g. {'min_age_years': 10, 'max_age_years': 12, 'min_gpa': 3.50}",
    )
    status = models.CharField(
        max_length=20,
        choices=CircularStatus.choices,
        default=CircularStatus.DRAFT,
        db_index=True,
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Admission Circular"
        verbose_name_plural = "Admission Circulars"
        ordering = ["-form_open_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "class_level"],
                name="unique_circular_per_session_class",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    def clean(self) -> None:
        super().clean()
        if self.session_id and self.session.institution_id != self.institution_id:
            raise ValidationError({"session": "Session must belong to the same institution."})
        if self.class_level_id and self.class_level.institution_id != self.institution_id:
            raise ValidationError(
                {"class_level": "Class level must belong to the same institution."}
            )
        if (
            self.form_open_date
            and self.form_close_date
            and self.form_open_date > self.form_close_date
        ):
            raise ValidationError(
                {"form_close_date": "Form close date must be on or after form open date."}
            )


class QuotaRule(TenantOwnedModel):
    """Quota reservation rule for an admission circular."""

    circular = models.ForeignKey(
        AdmissionCircular,
        on_delete=models.CASCADE,
        related_name="quota_rules",
    )
    quota_type = models.CharField(max_length=20, choices=QuotaType.choices)
    name = models.CharField(max_length=64, help_text="e.g. Freedom Fighter 5% Quota")
    reserved_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentage of total seats reserved",
    )
    reserved_seats = models.PositiveIntegerField(
        default=0,
        help_text="Absolute number of reserved seats (if percentage not used)",
    )
    priority = models.PositiveSmallIntegerField(default=1)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Quota Rule"
        verbose_name_plural = "Quota Rules"
        ordering = ["priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["circular", "quota_type"],
                name="unique_quota_per_circular",
            )
        ]

    def __str__(self) -> str:
        return f"{self.circular.title} - {self.name}"


class Application(TenantOwnedModel):
    """Prospective student admission application."""

    circular = models.ForeignKey(
        AdmissionCircular,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    application_no = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Unique human-readable identifier (e.g. ADM-2026-00001)",
    )
    # Student details
    name_bn = models.CharField(max_length=128, help_text="Applicant name in Bangla")
    name_en = models.CharField(max_length=128, help_text="Applicant name in English")
    dob = models.DateField(help_text="Date of birth")
    gender = models.CharField(max_length=10, choices=GenderChoices.choices)
    birth_reg_no = models.CharField(
        max_length=20,
        db_index=True,
        help_text="17-digit Bangladesh Birth Registration Number",
    )
    religion = models.CharField(
        max_length=20,
        choices=ReligionChoices.choices,
        default=ReligionChoices.ISLAM,
    )
    blood_group = models.CharField(
        max_length=10,
        choices=BloodGroupChoices.choices,
        default=BloodGroupChoices.UNKNOWN,
    )
    photo = models.ImageField(upload_to="admissions/photos/", null=True, blank=True)

    # Guardian details
    guardian_name = models.CharField(max_length=128)
    guardian_phone = models.CharField(max_length=20, help_text="+8801XXXXXXXXX")
    guardian_nid = models.CharField(
        max_length=20, blank=True, help_text="National ID (10/13/17 digits)"
    )
    guardian_relation = models.CharField(max_length=32, default="Father")

    # Address
    present_address = models.TextField()
    permanent_address = models.TextField()

    # Prior academic records
    previous_school = models.CharField(max_length=255, blank=True)
    previous_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    # Quota allocation
    quota_type = models.CharField(
        max_length=20,
        choices=QuotaType.choices,
        default=QuotaType.GENERAL,
    )
    quota_rule = models.ForeignKey(
        QuotaRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )

    # Lifecycle state machine
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Admission Application"
        verbose_name_plural = "Admission Applications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["circular", "birth_reg_no", "dob"],
                name="unique_applicant_per_circular",
            ),
            models.UniqueConstraint(
                fields=["institution", "application_no"],
                name="unique_application_no_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.application_no} - {self.name_en} ({self.get_status_display()})"

    def clean(self) -> None:
        super().clean()
        if self.circular_id and self.circular.institution_id != self.institution_id:
            raise ValidationError({"circular": "Circular must belong to the same institution."})


class ApplicationDocument(TenantOwnedModel):
    """Supporting verification document attached to an application."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=32,
        help_text="e.g. birth_certificate, previous_marksheet, guardian_nid, quota_certificate",
    )
    file = models.FileField(upload_to="admissions/documents/")
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Application Document"
        verbose_name_plural = "Application Documents"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.application.application_no} - {self.document_type}"


class ApplicationPayment(TenantOwnedModel):
    """Payment record for admission application fee."""

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BKASH,
    )
    transaction_id = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Application Payment"
        verbose_name_plural = "Application Payments"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.application.application_no} - ৳{self.amount} ({self.get_status_display()})"


class AdmissionTest(TenantOwnedModel):
    """Scheduled admission test for a circular."""

    circular = models.ForeignKey(
        AdmissionCircular,
        on_delete=models.CASCADE,
        related_name="tests",
    )
    title = models.CharField(max_length=128, help_text="e.g. Written Admission Test - Class 6")
    test_date = models.DateTimeField()
    venue = models.CharField(max_length=255, help_text="e.g. Main Campus Building 1")
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("100.00"))
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("40.00"))
    instructions = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Admission Test"
        verbose_name_plural = "Admission Tests"
        ordering = ["test_date"]

    def __str__(self) -> str:
        return f"{self.circular.title} - {self.title}"


class AdmissionTestResult(TenantOwnedModel):
    """Test result record for an applicant."""

    test = models.ForeignKey(
        AdmissionTest,
        on_delete=models.CASCADE,
        related_name="results",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="test_results",
    )
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2)
    is_passed = models.BooleanField(default=False)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Admission Test Result"
        verbose_name_plural = "Admission Test Results"
        ordering = ["-marks_obtained"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "application"],
                name="unique_test_result_per_applicant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.application.application_no} - {self.marks_obtained}/{self.test.total_marks}"


class LotteryDraw(TenantOwnedModel):
    """Lottery draw record using reproducible pseudo-random seed."""

    circular = models.ForeignKey(
        AdmissionCircular,
        on_delete=models.CASCADE,
        related_name="lottery_draws",
    )
    seed = models.BigIntegerField(help_text="PRNG seed for reproducible verification")
    draw_date = models.DateTimeField(auto_now_add=True)
    total_candidates = models.PositiveIntegerField()
    selected_candidates_count = models.PositiveIntegerField()
    drawn_order = models.JSONField(
        default=list,
        help_text="Ordered list of application IDs selected by the draw",
    )
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_lottery_draws",
    )
    is_confirmed = models.BooleanField(default=False)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Lottery Draw"
        verbose_name_plural = "Lottery Draws"
        ordering = ["-draw_date"]

    def __str__(self) -> str:
        return f"{self.circular.title} Lottery (Seed: {self.seed})"


class MeritList(TenantOwnedModel):
    """Merit list compiled from tests, lottery, or previous GPA."""

    circular = models.ForeignKey(
        AdmissionCircular,
        on_delete=models.CASCADE,
        related_name="merit_lists",
    )
    title = models.CharField(max_length=128, help_text="e.g. 1st Merit List 2026")
    selection_criteria = models.CharField(
        max_length=32,
        choices=[
            ("test_score", "Admission Test Score"),
            ("lottery", "Lottery Draw"),
            ("gpa", "Previous GPA"),
        ],
        default="test_score",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Merit List"
        verbose_name_plural = "Merit Lists"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.circular.title} - {self.title}"


class MeritListEntry(TenantOwnedModel):
    """Individual candidate rank in a merit list."""

    merit_list = models.ForeignKey(
        MeritList,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="merit_entries",
    )
    rank = models.PositiveIntegerField()
    merit_type = models.CharField(
        max_length=20,
        choices=MeritType.choices,
        default=MeritType.MERIT,
    )
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_selected = models.BooleanField(default=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Merit List Entry"
        verbose_name_plural = "Merit List Entries"
        ordering = ["merit_type", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["merit_list", "application"],
                name="unique_entry_per_merit_list",
            ),
            models.UniqueConstraint(
                fields=["merit_list", "merit_type", "rank"],
                name="unique_rank_per_merit_type",
            ),
        ]

    def __str__(self) -> str:
        return f"Rank #{self.rank} ({self.get_merit_type_display()}): {self.application.application_no}"
