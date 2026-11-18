"""Staff, HR, Leave, and Teacher Assignment models."""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class StaffType(models.TextChoices):
    SUPERADMIN = "superadmin", "Super Admin (সুপার অ্যাডমিন)"
    TEACHER = "teacher", "Teacher (শিক্ষক)"
    ADMIN = "admin", "Administrative Staff (প্রশাসনিক কর্মকর্তা)"
    SUPPORT = "support", "Support Staff (সহায়ক কর্মচারী)"
    DRIVER = "driver", "Driver (চালক)"
    SECURITY = "security", "Security (নিরাপত্তা কর্মী)"
    OTHER = "other", "Other (অন্যান্য)"


class StaffStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ON_LEAVE = "on_leave", "On Leave"
    SUSPENDED = "suspended", "Suspended"
    RESIGNED = "resigned", "Resigned"
    TERMINATED = "terminated", "Terminated"
    RETIRED = "retired", "Retired"


class LeaveRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending Recommendation"
    RECOMMENDED = "recommended", "Recommended by HOD"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class GenderRestriction(models.TextChoices):
    ALL = "all", "All Staff"
    MALE = "male", "Male Only"
    FEMALE = "female", "Female Only"


class Department(TenantOwnedModel, SoftDeleteMixin):
    """Academic or administrative department in the school."""

    name = models.CharField(
        max_length=100, help_text="e.g. Science, Mathematics, Bengali, Accounts"
    )
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(
        "Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
    )

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_active_department_per_institution",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Designation(TenantOwnedModel, SoftDeleteMixin):
    """Job title and organizational rank for school employees."""

    title = models.CharField(
        max_length=100, help_text="e.g. Principal, Senior Teacher, Assistant Teacher"
    )
    title_bn = models.CharField(max_length=100, blank=True, help_text="e.g. অধ্যক্ষ, সিনিয়র শিক্ষক")
    code = models.CharField(max_length=30, blank=True)
    rank_order = models.PositiveIntegerField(
        default=1,
        help_text="Hierarchy rank: lower number represents higher seniority",
    )
    role_category = models.CharField(
        max_length=30,
        choices=StaffType.choices,
        default=StaffType.TEACHER,
    )

    class Meta:
        verbose_name = "Designation"
        verbose_name_plural = "Designations"
        ordering = ["rank_order", "title"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "title"],
                condition=models.Q(is_deleted=False),
                name="unique_active_designation_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_role_category_display()})"


class Staff(TenantOwnedModel, SoftDeleteMixin):
    """Master employee record for teaching and non-teaching personnel."""

    employee_id = models.CharField(
        max_length=32,
        db_index=True,
        help_text="Institution-scoped sequential ID, e.g. EMP-2026-00001",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_profile",
        help_text="Optional linked portal login user",
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_members",
    )
    designation = models.ForeignKey(
        Designation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_members",
    )
    branch = models.ForeignKey(
        "institutions.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_members",
        help_text="Primary campus/branch where this staff member is assigned",
    )
    staff_type = models.CharField(
        max_length=30,
        choices=StaffType.choices,
        default=StaffType.TEACHER,
        db_index=True,
    )
    full_name_en = models.CharField(max_length=150, db_index=True)
    full_name_bn = models.CharField(max_length=150, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
    )
    dob = models.DateField(help_text="Date of birth")
    blood_group = models.CharField(max_length=10, blank=True)
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
    present_address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    photo = models.FileField(upload_to="staff/photos/%Y/%m/", blank=True, null=True)

    joining_date = models.DateField(help_text="Official joining date in this institution")
    confirmation_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StaffStatus.choices,
        default=StaffStatus.ACTIVE,
        db_index=True,
    )

    # Bangladeshi MPO (Monthly Pay Order) & Tax specifics
    is_mpo = models.BooleanField(
        default=False,
        help_text="Designates whether salary is government-subsidized under Monthly Pay Order",
    )
    mpo_index_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Government MPO Index Number issued by DSHE / DTE / Madrasah Board",
    )
    tin_number = models.CharField(
        max_length=30, blank=True, help_text="Taxpayer Identification Number"
    )

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"
        ordering = ["designation__rank_order", "full_name_en"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "employee_id"],
                name="unique_employee_id_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "phone"],
                condition=models.Q(is_deleted=False),
                name="unique_active_staff_phone_per_institution",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["phone", "institution"]),
            models.Index(fields=["nid", "institution"]),
            models.Index(fields=["mpo_index_number", "institution"]),
            models.Index(fields=["full_name_en", "institution"]),
        ]

    def __str__(self) -> str:
        desig = f" ({self.designation.title})" if self.designation else ""
        return f"{self.employee_id} - {self.full_name_en}{desig}"


class StaffEducation(TenantOwnedModel):
    """Academic credentials and degree records of staff."""

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="educations")
    degree_title = models.CharField(max_length=100, help_text="e.g. B.Sc in Mathematics, B.Ed, M.A")
    institution_name = models.CharField(max_length=150)
    board_or_university = models.CharField(max_length=100)
    passing_year = models.PositiveIntegerField()
    result = models.CharField(max_length=50, help_text="e.g. GPA 3.75, First Class, Division 1")

    class Meta:
        ordering = ["-passing_year"]

    def __str__(self) -> str:
        return f"{self.degree_title} ({self.passing_year}) - {self.staff.full_name_en}"


class StaffDocument(TenantOwnedModel):
    """Digital verification documents associated with staff employment."""

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(
        max_length=50,
        choices=[
            ("nid", "National ID (NID)"),
            ("appointment_letter", "Appointment Letter (নিয়োগপত্র)"),
            ("joining_letter", "Joining Report (যোগদানপত্র)"),
            ("mpo_order", "MPO Enlistment Order (এমপিও আদেশ)"),
            ("certificate", "Educational Certificate"),
            ("police_clearance", "Police Clearance"),
            ("other", "Other Document"),
        ],
        default="certificate",
    )
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to="staff/documents/%Y/%m/")
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} for {self.staff.full_name_en}"


class StaffIDCard(TenantOwnedModel, SoftDeleteMixin):
    """Official employee ID card record."""

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="id_cards")
    card_number = models.CharField(max_length=50, db_index=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    rfid_uid = models.CharField(max_length=64, blank=True)
    qr_payload = models.TextField(blank=True)

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self) -> str:
        return f"Card {self.card_number} ({self.staff.full_name_en})"


class LeaveType(TenantOwnedModel, SoftDeleteMixin):
    """Institutional leave categories with yearly quotas."""

    name = models.CharField(max_length=100, help_text="e.g. Casual Leave, Medical Leave")
    name_bn = models.CharField(
        max_length=100, blank=True, help_text="e.g. নৈমিত্তিক ছুটি, অসুস্থতাজনিত ছুটি"
    )
    code = models.CharField(max_length=20, help_text="e.g. CL, ML, MAT, EL, SPL")
    yearly_quota = models.PositiveIntegerField(
        default=14, help_text="Standard allocated annual days"
    )
    is_paid = models.BooleanField(default=True)
    allow_carry_forward = models.BooleanField(default=False)
    max_carry_forward_days = models.PositiveIntegerField(default=0)
    gender_restriction = models.CharField(
        max_length=10,
        choices=GenderRestriction.choices,
        default=GenderRestriction.ALL,
    )

    class Meta:
        ordering = ["name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_leave_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class LeaveBalance(TenantOwnedModel):
    """Annual leave balance tracking per employee per academic session."""

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="balances")
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="staff_leave_balances",
    )
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    carried_forward_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    pending_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        ordering = ["leave_type__name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["staff", "leave_type", "session"],
                name="unique_staff_leave_balance_per_session",
            )
        ]

    @property
    def remaining_days(self) -> Decimal:
        return self.allocated_days + self.carried_forward_days - self.used_days - self.pending_days

    def __str__(self) -> str:
        return (
            f"{self.staff.full_name_en} - {self.leave_type.code}: {self.remaining_days} remaining"
        )


class LeaveRequest(TenantOwnedModel, SoftDeleteMixin):
    """Leave application lifecycle tracking."""

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="requests")
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="staff_leave_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days_count = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.PENDING,
        db_index=True,
    )
    attachment = models.FileField(upload_to="staff/leaves/%Y/%m/", blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    recommender = models.ForeignKey(
        Staff,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recommended_leaves",
    )
    approver = models.ForeignKey(
        Staff,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_leaves",
    )
    rejection_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.staff.full_name_en} | {self.leave_type.code} ({self.start_date} to {self.end_date}): {self.status}"


class TeacherAssignment(TenantOwnedModel):
    """Assignment of teacher to a specific subject, class section, and academic session."""

    teacher = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="teaching_assignments"
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )
    periods_per_week = models.PositiveIntegerField(default=0)
    is_primary_teacher = models.BooleanField(
        default=False,
        help_text="Designates the primary lead instructor for this subject in the section",
    )

    class Meta:
        ordering = ["section", "subject"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["teacher", "subject", "section", "session"],
                name="unique_teacher_subject_section_session",
            )
        ]

    def __str__(self) -> str:
        return f"{self.teacher.full_name_en} -> {self.section} ({self.subject.name_en})"
