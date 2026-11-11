"""Guardian and Family models."""

from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class GuardianRelation(models.TextChoices):
    """Recognized familial and guardian relationships in Bangladeshi schools."""

    FATHER = "father", "Father (পিতা)"
    MOTHER = "mother", "Mother (মাতা)"
    BROTHER = "brother", "Brother (ভাই)"
    SISTER = "sister", "Sister (বোন)"
    UNCLE = "uncle", "Uncle (চাচা/মামা/ফুফা/খালু)"
    AUNT = "aunt", "Aunt (ফুফু/খালা/চাচী/মামী)"
    GRANDPARENT = "grandparent", "Grandparent (দাদা/দাদী/নানা/নানী)"
    LEGAL_GUARDIAN = "legal_guardian", "Legal Guardian (আইনগত অভিভাবক)"
    OTHER = "other", "Other (অন্যান্য)"


class Family(TenantOwnedModel, SoftDeleteMixin):
    """Grouping entity connecting siblings and primary contacts under a single household."""

    family_code = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Institution-scoped family code, e.g. FAM-2026-00001",
    )
    name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Family household title, e.g. 'Ahmed Family' or 'রহমান পরিবার'",
    )
    primary_contact_phone = models.CharField(
        max_length=20,
        db_index=True,
        blank=True,
        help_text="Primary communication mobile number (+8801XXXXXXXXX)",
    )
    address = models.TextField(blank=True, help_text="Common family residential address")
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Family"
        verbose_name_plural = "Families"
        ordering = ["-created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "family_code"],
                name="unique_family_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.family_code} - {self.name or self.primary_contact_phone}"


class Guardian(TenantOwnedModel, SoftDeleteMixin):
    """Master guardian and parent record for students in an institution."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardian_profiles",
        help_text="Portal login account if activated",
    )
    family = models.ForeignKey(
        Family,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardians",
        help_text="Linked household family",
    )
    name_en = models.CharField(max_length=150, db_index=True)
    name_bn = models.CharField(max_length=150, blank=True)
    relation_default = models.CharField(
        max_length=30,
        choices=GuardianRelation.choices,
        default=GuardianRelation.FATHER,
    )
    phone = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Primary mobile number in normalized format (+8801XXXXXXXXX)",
    )
    alt_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    nid = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Bangladeshi National ID number (10, 13, or 17 digits)",
    )
    occupation = models.CharField(max_length=100, blank=True)
    annual_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual household income in BDT",
    )
    present_address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    photo = models.FileField(upload_to="guardians/photos/%Y/%m/", blank=True, null=True)
    is_emergency_contact = models.BooleanField(
        default=False,
        help_text="Default emergency call contact flag",
    )

    class Meta:
        verbose_name = "Guardian"
        verbose_name_plural = "Guardians"
        ordering = ["-created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "phone"],
                condition=models.Q(is_deleted=False),
                name="unique_active_guardian_phone_per_institution",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["phone", "institution"]),
            models.Index(fields=["nid", "institution"]),
            models.Index(fields=["name_en", "institution"]),
        ]

    def __str__(self) -> str:
        return f"{self.name_en} ({self.phone})"


class StudentGuardian(TenantOwnedModel):
    """Many-to-many relationship mapping students to guardians with permissions and flags."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="guardian_relations",
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name="student_relations",
    )
    relation = models.CharField(
        max_length=30,
        choices=GuardianRelation.choices,
        default=GuardianRelation.FATHER,
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Indicates primary contact receiving report cards and primary calls",
    )
    can_pickup = models.BooleanField(
        default=True,
        help_text="Authorized to collect the student from school premises",
    )
    receives_sms = models.BooleanField(
        default=True,
        help_text="Receives automated attendance and notification SMS",
    )
    financial_responsible = models.BooleanField(
        default=False,
        help_text="Responsible for paying academic fees and dues",
    )

    class Meta:
        verbose_name = "Student Guardian"
        verbose_name_plural = "Student Guardians"
        ordering = ["-is_primary", "-created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["student", "guardian"],
                name="unique_student_guardian_link",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "is_primary"]),
        ]

    def __str__(self) -> str:
        return f"{self.guardian.name_en} -> {self.student.name_en} ({self.get_relation_display()})"


class AuthorizedPickup(TenantOwnedModel, SoftDeleteMixin):
    """Third-party individual authorized by parents to pick up the student."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="authorized_pickups",
    )
    name = models.CharField(max_length=150)
    relation = models.CharField(
        max_length=50,
        help_text="Relation to student e.g. Driver, Grandparent, Neighbor",
    )
    phone = models.CharField(max_length=20, db_index=True)
    nid = models.CharField(max_length=30, blank=True)
    photo = models.FileField(upload_to="guardians/pickups/%Y/%m/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    otp_verified = models.BooleanField(
        default=False,
        help_text="Indicates whether this pickup person was verified via guardian OTP",
    )
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Authorized Pickup Person"
        verbose_name_plural = "Authorized Pickup Persons"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.relation}) for {self.student.name_en}"
