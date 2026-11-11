"""Data models for Fee Structures, Invoicing, Waivers, and Fines."""

from decimal import Decimal

from django.db import models

from apps.accounts.models import User
from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class FeeType(models.TextChoices):
    TUITION = "tuition", "Monthly Tuition Fee (বেতন)"
    ADMISSION = "admission", "Admission Fee (ভর্তি ফি)"
    EXAM = "exam", "Examination Fee (পরীক্ষার ফি)"
    SESSION_CHARGE = "session_charge", "Session Charge (সেশন চার্জ)"
    LAB = "lab", "Laboratory Fee (ল্যাব ফি)"
    LIBRARY = "library", "Library Fee (লাইব্রেরি ফি)"
    TRANSPORT = "transport", "Transport Fee (যাতায়াত ফি)"
    HOSTEL = "hostel", "Hostel Fee (হোস্টেল ফি)"
    SPORTS = "sports", "Sports & Cultural (ক্রীড়া ও সাংস্কৃতিক)"
    ID_CARD = "id_card", "Student ID Card (পরিচয়পত্র)"
    LATE_FINE = "late_fine", "Late Fine (বিলম্ব ফি)"
    OTHER = "other", "Other Fee (অন্যান্য)"


class RecurrenceType(models.TextChoices):
    ONE_TIME = "one_time", "One Time"
    MONTHLY = "monthly", "Monthly"
    TERMLY = "termly", "Termly / Per Exam"
    ANNUALLY = "annually", "Annually"


class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage (%)"
    FLAT = "flat", "Flat Amount (BDT)"


class WaiverCategory(models.TextChoices):
    SIBLING = "sibling", "Sibling Concession (সহোদর সুবিধা)"
    MERIT = "merit", "Merit / Academic Scholarship (মেধাবৃত্তি)"
    POOR_FUND = "poor_fund", "Poor Fund / Zakat / Financial Need (দরিদ্র তহবিল)"
    QUOTA = "quota", "Freedom Fighter / Special Quota (মুক্তিযোদ্ধা/বিশেষ কোটা)"
    STAFF_CHILD = "staff_child", "Staff / Teacher Child (শিক্ষক সন্তান সুবিধা)"
    SPECIAL = "special", "Discretionary / Special (বিশেষ বিবেচনা)"


class WaiverApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class FineType(models.TextChoices):
    FIXED = "fixed", "Fixed Amount"
    DAILY = "daily", "Daily Accrual"
    SLAB = "slab", "Tiered / Slab-Based"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PARTIALLY_PAID = "partially_paid", "Partially Paid"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    CANCELLED = "cancelled", "Cancelled"
    WAIVED = "waived", "Waived"


class InvoiceType(models.TextChoices):
    MONTHLY = "monthly", "Monthly Tuition & Regular Fees"
    TERMLY = "termly", "Termly / Examination"
    ADMISSION = "admission", "Admission & Initial Enrollment"
    SESSION = "session", "Annual Session Charge"
    CUSTOM = "custom", "Custom / Miscellaneous"


class FeeHead(TenantOwnedModel, SoftDeleteMixin):
    """Institutional category of fees."""

    code = models.CharField(
        max_length=50,
        help_text="Unique short code per institution (e.g. TUITION, ADMISSION).",
    )
    name_en = models.CharField(max_length=255, help_text="Fee head name in English.")
    name_bn = models.CharField(max_length=255, help_text="Fee head name in Bengali script.")
    fee_type = models.CharField(
        max_length=30, choices=FeeType.choices, default=FeeType.TUITION, db_index=True
    )
    recurrence = models.CharField(
        max_length=20, choices=RecurrenceType.choices, default=RecurrenceType.MONTHLY
    )
    is_optional = models.BooleanField(
        default=False, help_text="If True, fee is opt-in for students (e.g. transport, club)."
    )
    is_refundable = models.BooleanField(
        default=False, help_text="If True, fee represents a refundable deposit."
    )
    is_active = models.BooleanField(default=True)
    account_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Accounting general ledger code (Task 17 linkage).",
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=models.Q(is_deleted=False),
                name="unique_fee_head_code_per_institution",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "fee_type"]),
            models.Index(fields=["institution", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name_en} ({self.name_bn}) [{self.code}]"


class FeeStructure(TenantOwnedModel, SoftDeleteMixin):
    """Class and session-level fee template aggregating standard fee heads."""

    session = models.ForeignKey(
        "institutions.AcademicSession", on_delete=models.CASCADE, related_name="fee_structures"
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel", on_delete=models.CASCADE, related_name="fee_structures"
    )
    group = models.ForeignKey(
        "academics.Group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fee_structures",
        help_text="Optional academic group (Science, Commerce, Humanities).",
    )
    name = models.CharField(max_length=255, help_text="e.g. Class 9 Science 2026 Regular")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["session", "class_level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "session", "class_level", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_fee_structure_per_class_session",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "session", "class_level"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.class_level.name} ({self.session.name})"


class FeeStructureItem(TenantOwnedModel):
    """Line item linking a FeeHead to a FeeStructure with a specified amount."""

    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name="items")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.PROTECT, related_name="structure_items")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount in BDT (৳).")
    due_day = models.PositiveSmallIntegerField(
        default=10, help_text="Day of month when payment is due (e.g. 10th)."
    )
    applicable_months = models.JSONField(
        default=list,
        blank=True,
        help_text="List of integer months (1-12) when applicable. Empty means all months or non-monthly.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fee_structure", "fee_head"],
                name="unique_fee_head_per_structure",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gte=Decimal("0.00")),
                name="fee_structure_item_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["fee_structure", "fee_head"]),
        ]

    def __str__(self) -> str:
        return f"{self.fee_head.name_en}: ৳{self.amount}"


class StudentFeeAssignment(TenantOwnedModel, SoftDeleteMixin):
    """Personalized student fee head assignment, override rate, or exemption."""

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="fee_assignments"
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_assignments",
    )
    fee_head = models.ForeignKey(FeeHead, on_delete=models.CASCADE)
    custom_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Custom assigned rate in BDT, overriding standard structure.",
    )
    is_exempt = models.BooleanField(
        default=False, help_text="If True, student is 100% exempt from this fee head."
    )
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "fee_head"],
                condition=models.Q(is_deleted=False),
                name="unique_student_fee_assignment",
            ),
            models.CheckConstraint(
                check=models.Q(custom_amount__isnull=True)
                | models.Q(custom_amount__gte=Decimal("0.00")),
                name="student_fee_assignment_custom_amount_non_negative",
            ),
        ]


class WaiverRule(TenantOwnedModel, SoftDeleteMixin):
    """Institutional discount or scholarship rule."""

    name = models.CharField(max_length=255, help_text="e.g. Sibling Concession 50%")
    category = models.CharField(
        max_length=30, choices=WaiverCategory.choices, default=WaiverCategory.MERIT
    )
    discount_type = models.CharField(
        max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Percentage (e.g. 50.00) or flat BDT amount (e.g. 500.00).",
    )
    max_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional ceiling limit in BDT for percentage waivers.",
    )
    applicable_fee_heads = models.ManyToManyField(
        FeeHead,
        blank=True,
        related_name="waiver_rules",
        help_text="Fee heads this waiver applies to. If empty, applies to Tuition only by default.",
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_value__gte=Decimal("0.00")),
                name="waiver_rule_discount_value_non_negative",
            )
        ]

    def __str__(self) -> str:
        unit = "%" if self.discount_type == DiscountType.PERCENTAGE else "৳"
        return f"{self.name} ({self.discount_value}{unit})"


class StudentWaiver(TenantOwnedModel, SoftDeleteMixin):
    """Allocated student waiver with two-stage approval workflow."""

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="waivers"
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="waivers",
    )
    waiver_rule = models.ForeignKey(
        WaiverRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_waivers"
    )
    title = models.CharField(
        max_length=255, blank=True, default="", help_text="e.g. Merit Scholarship (Term 1)"
    )
    discount_type = models.CharField(
        max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    max_discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    applicable_fee_heads = models.ManyToManyField(
        FeeHead, blank=True, related_name="student_waiver_items"
    )
    status = models.CharField(
        max_length=20,
        choices=WaiverApprovalStatus.choices,
        default=WaiverApprovalStatus.PENDING,
        db_index=True,
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_student_waivers",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_value__gte=Decimal("0.00")),
                name="student_waiver_discount_value_non_negative",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "student", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.title or 'Waiver'} [{self.status}]"


class FineRule(TenantOwnedModel, SoftDeleteMixin):
    """Institutional late payment fine calculation rule."""

    name = models.CharField(max_length=255, help_text="e.g. Standard Late Fine (5 Days Grace)")
    fine_type = models.CharField(max_length=20, choices=FineType.choices, default=FineType.FIXED)
    grace_period_days = models.PositiveSmallIntegerField(
        default=5, help_text="Days past due date before fine starts accruing."
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Fixed late fine or daily accrual rate in BDT.",
    )
    max_fine_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum ceiling for accrued fines in BDT.",
    )
    slab_config = models.JSONField(
        default=list,
        blank=True,
        help_text="Tiered slabs list: [{'min_days': 1, 'max_days': 10, 'amount': 50.00}, ...]",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=Decimal("0.00")),
                name="fine_rule_amount_non_negative",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} (Grace: {self.grace_period_days}d)"


class Invoice(TenantOwnedModel, SoftDeleteMixin):
    """Master billing invoice for a student."""

    invoice_number = models.CharField(
        max_length=32, db_index=True, help_text="Human-friendly number: INV-2026-000001"
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="invoices"
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="invoices",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession", on_delete=models.CASCADE, related_name="invoices"
    )
    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.MONTHLY
    )
    title = models.CharField(
        max_length=255, blank=True, default="", help_text="e.g. Tuition Fee - March 2026"
    )
    billing_month = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="1 to 12 for monthly invoices."
    )
    billing_year = models.PositiveSmallIntegerField(default=2026)

    # Monetary summary fields (BDT)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    waiver_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fine_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    fine_rule = models.ForeignKey(
        FineRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    fine_evaluated_at = models.DateTimeField(null=True, blank=True)
    pdf_receipt = models.FileField(upload_to="fees/invoices/%Y/%m/", null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-issue_date", "-invoice_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "invoice_number"],
                condition=models.Q(is_deleted=False),
                name="unique_invoice_number_per_institution",
            ),
            models.CheckConstraint(
                check=models.Q(subtotal_amount__gte=Decimal("0.00"))
                & models.Q(waiver_amount__gte=Decimal("0.00"))
                & models.Q(fine_amount__gte=Decimal("0.00"))
                & models.Q(total_payable__gte=Decimal("0.00"))
                & models.Q(paid_amount__gte=Decimal("0.00"))
                & models.Q(due_amount__gte=Decimal("0.00")),
                name="invoice_amounts_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["institution", "student", "status"]),
            models.Index(fields=["institution", "billing_year", "billing_month"]),
            models.Index(fields=["institution", "status", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} - {self.student.student_id} (৳{self.total_payable})"

    def clean(self) -> None:
        expected_payable = max(
            Decimal("0.00"), self.subtotal_amount - self.waiver_amount + self.fine_amount
        )
        if self.total_payable != expected_payable:
            self.total_payable = expected_payable
        self.due_amount = max(Decimal("0.00"), self.total_payable - self.paid_amount)


class InvoiceLine(TenantOwnedModel):
    """Item breakdown line within an invoice."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.PROTECT, related_name="invoice_lines")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    waiver_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fine_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "fee_head"],
                name="unique_fee_head_per_invoice",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gte=Decimal("0.00"))
                & models.Q(waiver_amount__gte=Decimal("0.00"))
                & models.Q(payable_amount__gte=Decimal("0.00")),
                name="invoice_line_amounts_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["invoice", "fee_head"]),
        ]

    def __str__(self) -> str:
        return f"{self.description}: ৳{self.payable_amount}"


class InvoiceSequence(TenantOwnedModel):
    """Institutional gap-free sequential invoice counter."""

    year = models.PositiveSmallIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "year"],
                name="unique_invoice_sequence_per_institution_year",
            )
        ]

    def __str__(self) -> str:
        return f"{self.institution.name} {self.year}: #{self.last_number}"
