"""Institution and tenancy core models."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel, TenantOwnedModel


class MPOStatus(models.TextChoices):
    NON_MPO = "non_mpo", "Non-MPO"
    MPO = "mpo", "MPO"
    PARTIAL_MPO = "partial_mpo", "Partial MPO"


class EducationBoard(models.TextChoices):
    DHAKA = "dhaka", "Dhaka"
    RAJSHAHI = "rajshahi", "Rajshahi"
    CHITTAGONG = "chittagong", "Chittagong"
    COMILLA = "comilla", "Comilla"
    JESSORE = "jessore", "Jessore"
    BARISAL = "barisal", "Barisal"
    SYLHET = "sylhet", "Sylhet"
    DINAJPUR = "dinajpur", "Dinajpur"
    MYMENSINGH = "mymensingh", "Mymensingh"
    MADRASAH = "madrasah", "Madrasah"
    TECHNICAL = "technical", "Technical"
    CAMBRIDGE = "cambridge", "Cambridge"
    EDEXCEL = "edexcel", "Edexcel"
    IB = "ib", "International Baccalaureate"


class InstitutionType(models.TextChoices):
    PRIMARY = "primary", "Primary (Class 1-5)"
    SECONDARY = "secondary", "Secondary (Class 6-10)"
    HIGHER_SECONDARY = "higher_secondary", "Higher Secondary (Class 11-12)"
    COLLEGE = "college", "Degree College"
    MADRASA = "madrasa", "Madrasa (Dakhil/Alim)"
    KINDERGARTEN = "kindergarten", "Kindergarten"


class ShiftName(models.TextChoices):
    MORNING = "morning", "Morning"
    DAY = "day", "Day"
    EVENING = "evening", "Evening"


class MediumChoices(models.TextChoices):
    BANGLA = "bangla", "Bangla Medium"
    ENGLISH = "english", "English Medium"
    ENGLISH_VERSION = "english_version", "English Version"
    MADRASA = "madrasa", "Madrasa"


class SessionStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"


class HolidayType(models.TextChoices):
    GOVT = "govt", "Government Public Holiday"
    INSTITUTIONAL = "institutional", "Institutional Holiday"
    EMERGENCY = "emergency", "Emergency Closure"


def default_weekend_days() -> list[str]:
    return ["friday", "saturday"]


def default_institution_settings() -> dict[str, Any]:
    return {
        "grading_profile_id": None,
        "attendance_defaults": {
            "late_tolerance_minutes": 15,
            "half_day_minimum_minutes": 180,
        },
        "sms_sender_id": "",
        "fee_receipt_prefix": "REC-",
        "bangla_digits": True,
    }


class Institution(BaseModel):
    """The root tenant entity representing an educational institution (school/college)."""

    name_bn = models.CharField(max_length=255, verbose_name="Name (Bangla)")
    name_en = models.CharField(max_length=255, verbose_name="Name (English)")
    eiin = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="EIIN",
        help_text="Educational Institute Identification Number (e.g. 134567)",
    )
    mpo_status = models.CharField(
        max_length=20,
        choices=MPOStatus.choices,
        default=MPOStatus.NON_MPO,
        verbose_name="MPO Status",
    )
    board = models.CharField(
        max_length=30,
        choices=EducationBoard.choices,
        default=EducationBoard.DHAKA,
        verbose_name="Education Board",
    )
    type = models.CharField(
        max_length=30,
        choices=InstitutionType.choices,
        default=InstitutionType.SECONDARY,
        verbose_name="Institution Type",
    )

    # Address Details
    division = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    upazila = models.CharField(max_length=100)
    address_line = models.TextField(blank=True)

    # Contact Details
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Brand Assets
    logo = models.ImageField(upload_to="institutions/logos/", null=True, blank=True)
    seal = models.ImageField(upload_to="institutions/seals/", null=True, blank=True)
    signature = models.ImageField(upload_to="institutions/signatures/", null=True, blank=True)

    # Localization Defaults
    timezone = models.CharField(max_length=50, default="Asia/Dhaka")
    currency = models.CharField(max_length=10, default="BDT")
    weekend_days = models.JSONField(default=default_weekend_days)

    # Flexible Settings JSON
    settings = models.JSONField(default=default_institution_settings, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        verbose_name = "Institution"
        verbose_name_plural = "Institutions"

    def __str__(self) -> str:
        return f"{self.name_en} ({self.eiin or 'No EIIN'})"

    @property
    def name(self) -> str:
        return self.name_en

    @property
    def address(self) -> str:
        parts = [self.address_line, self.upazila, self.district, self.division]
        return ", ".join([p for p in parts if p])


class Branch(TenantOwnedModel):
    """Campuses/branches belonging to an institution."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, help_text="Short unique branch code (e.g. MAIN, DHAN)")
    address = models.TextField(blank=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        ordering = ["code"]
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_branch_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Shift(TenantOwnedModel):
    """Operational shifts within a branch (e.g. Morning, Day)."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="shifts")
    name = models.CharField(max_length=50, choices=ShiftName.choices, default=ShiftName.MORNING)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["branch", "start_time"]
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                name="unique_shift_name_per_branch",
            )
        ]

    def __str__(self) -> str:
        return f"{self.branch.code} - {self.get_name_display()} ({self.start_time}-{self.end_time})"

    def clean(self) -> None:
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Shift start time must be before end time.")


class AcademicSession(TenantOwnedModel):
    """Academic year/session (e.g. 2026). Exactly one session can be current per institution."""

    name = models.CharField(max_length=100, help_text="Session name (e.g. 2026)")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.PLANNED,
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Academic Session"
        verbose_name_plural = "Academic Sessions"
        constraints = [
            # Ensure at most one current session per institution
            models.UniqueConstraint(
                fields=["institution"],
                condition=models.Q(is_current=True),
                name="unique_current_session_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_session_name_per_institution",
            ),
        ]

    def __str__(self) -> str:
        current_badge = " [Current]" if self.is_current else ""
        return f"{self.name} ({self.status}){current_badge}"

    def clean(self) -> None:
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("Session start date must be strictly before end date.")


class Term(TenantOwnedModel):
    """Terms/semesters within an academic session (e.g. First Term, Half-Yearly, Annual)."""

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["session", "order"]
        verbose_name = "Term"
        verbose_name_plural = "Terms"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "name"],
                name="unique_term_name_per_session",
            ),
            models.UniqueConstraint(
                fields=["session", "order"],
                name="unique_term_order_per_session",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.session.name} - {self.name} (Term {self.order})"

    def clean(self) -> None:
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("Term start date must be strictly before end date.")
        if self.session_id:
            if self.start_date < self.session.start_date or self.end_date > self.session.end_date:
                raise ValidationError(
                    "Term dates must fall within the academic session date range."
                )


class Holiday(TenantOwnedModel):
    """Institutional or government holidays used for academic calendars and attendance calculation."""

    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=30,
        choices=HolidayType.choices,
        default=HolidayType.GOVT,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    applies_to_all_branches = models.BooleanField(default=True)
    branches = models.ManyToManyField(Branch, blank=True, related_name="holidays")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Holiday"
        verbose_name_plural = "Holidays"

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} to {self.end_date})"

    def clean(self) -> None:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Holiday start date cannot be after end date.")
