"""Payroll, Salary Structure, Loan, and Payslip models."""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class ComponentType(models.TextChoices):
    EARNING = "earning", "Earning (আয় / ভাতা)"
    DEDUCTION = "deduction", "Deduction (কর্তন)"


class CalculationType(models.TextChoices):
    FIXED = "fixed", "Fixed Amount (নির্দিষ্ট)"
    PERCENTAGE_OF_BASIC = "percentage_of_basic", "% of Basic Salary (মূল বেতনের %)"
    PERCENTAGE_OF_GROSS = "percentage_of_gross", "% of Gross Salary (মোট বেতনের %)"


class SalaryPaymentMethod(models.TextChoices):
    BANK_TRANSFER = "bank_transfer", "Bank Transfer / BEFTN (ব্যাংক)"
    CASH = "cash", "Cash in Hand (নগদ)"
    CHEQUE = "cheque", "Bank Cheque (চেক)"
    MFS = "mfs", "Mobile Financial Service (bKash / Nagad)"


class LoanType(models.TextChoices):
    ADVANCE = "advance", "Salary Advance (অগ্রিম বেতন)"
    LOAN = "loan", "Institutional Loan (ঋণ)"


class LoanStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    PAUSED = "paused", "Paused"


class PayrollRunStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REVIEWED = "reviewed", "Reviewed"
    APPROVED = "approved", "Approved"
    PAID = "paid", "Paid"
    LOCKED = "locked", "Locked"


class AbsenceDeductionBasis(models.TextChoices):
    BASIC = "basic", "Pro-rata of Basic Salary"
    GROSS = "gross", "Pro-rata of Gross Salary"


class SalaryComponent(TenantOwnedModel, SoftDeleteMixin):
    """Configurable salary earning or deduction component per institution."""

    code = models.CharField(
        max_length=40,
        db_index=True,
        help_text="Short unique code (e.g. BASIC, HRA, MED, CONV, PF, TDS).",
    )
    name_en = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True)
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices,
        default=ComponentType.EARNING,
        db_index=True,
    )
    calculation_type = models.CharField(
        max_length=30,
        choices=CalculationType.choices,
        default=CalculationType.FIXED,
    )
    default_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Fixed BDT amount or percentage value (e.g. 40.00 for 40%).",
    )
    is_taxable = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System-seeded standard component.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveIntegerField(default=10)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Salary Component"
        verbose_name_plural = "Salary Components"
        ordering = ["component_type", "display_order", "name_en"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_salary_component_code",
            ),
            models.CheckConstraint(
                check=models.Q(default_value__gte=Decimal("0.00")),
                name="salary_component_default_value_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.name_en} ({self.get_component_type_display()})"


class SalaryStructure(TenantOwnedModel, SoftDeleteMixin):
    """Reusable salary structure template (e.g. Senior Teacher Grade)."""

    code = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Salary Structure"
        verbose_name_plural = "Salary Structures"
        ordering = ["name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_salary_structure_code",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class SalaryStructureLine(TenantOwnedModel):
    """Component formula row belonging to a SalaryStructure."""

    structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name="structure_lines",
    )
    calculation_type = models.CharField(
        max_length=30,
        choices=CalculationType.choices,
        default=CalculationType.FIXED,
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Salary Structure Line"
        verbose_name_plural = "Salary Structure Lines"
        ordering = ["component__component_type", "component__display_order"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["structure", "component"],
                name="unique_component_per_salary_structure",
            ),
            models.CheckConstraint(
                check=models.Q(value__gte=Decimal("0.00")),
                name="salary_structure_line_value_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.structure.code} -> {self.component.code}: {self.value}"


class StaffSalaryProfile(TenantOwnedModel, SoftDeleteMixin):
    """Active salary structure, banking, MPO split, and PF profile per employee."""

    staff = models.OneToOneField(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="salary_profile",
    )
    structure = models.ForeignKey(
        SalaryStructure,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_profiles",
    )
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monthly basic salary in BDT (মূল বেতন).",
    )
    mpo_portion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Government MPO disbursed portion for MPO-enlisted teachers.",
    )
    institutional_portion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="School-funded top-up portion.",
    )

    # Payment & Banking Details (Confidential)
    payment_method = models.CharField(
        max_length=20,
        choices=SalaryPaymentMethod.choices,
        default=SalaryPaymentMethod.BANK_TRANSFER,
    )
    bank_name = models.CharField(max_length=120, blank=True)
    bank_branch = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=60, blank=True)
    bank_routing_number = models.CharField(max_length=30, blank=True)
    mfs_number = models.CharField(max_length=20, blank=True)

    # Provident Fund & Attendance Deduction Rules
    pf_enrolled = models.BooleanField(default=False)
    pf_employee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
    )
    pf_employer_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
    )
    late_deduction_enabled = models.BooleanField(
        default=True,
        help_text="Deduct salary after accumulating configurable late days.",
    )
    late_days_per_absent = models.PositiveSmallIntegerField(
        default=3,
        help_text="Number of late arrivals treated as 1 absent day deduction (0 = disabled).",
    )
    overtime_hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    effective_from = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Staff Salary Profile"
        verbose_name_plural = "Staff Salary Profiles"
        ordering = ["staff__employee_id"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                check=models.Q(basic_salary__gte=Decimal("0.00")),
                name="staff_basic_salary_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(mpo_portion__gte=Decimal("0.00")),
                name="staff_mpo_portion_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(institutional_portion__gte=Decimal("0.00")),
                name="staff_institutional_portion_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff.employee_id} - {self.staff.full_name_en} (Basic: ৳{self.basic_salary})"


class StaffSalaryOverride(TenantOwnedModel):
    """Per-employee component override over their assigned SalaryStructure."""

    profile = models.ForeignKey(
        StaffSalaryProfile,
        on_delete=models.CASCADE,
        related_name="overrides",
    )
    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name="staff_overrides",
    )
    calculation_type = models.CharField(
        max_length=30,
        choices=CalculationType.choices,
        default=CalculationType.FIXED,
    )
    value = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Staff Salary Override"
        verbose_name_plural = "Staff Salary Overrides"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["profile", "component"],
                name="unique_override_component_per_profile",
            ),
            models.CheckConstraint(
                check=models.Q(value__gte=Decimal("0.00")),
                name="staff_salary_override_value_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile.staff.employee_id} override {self.component.code}: {self.value}"


class StaffLoan(TenantOwnedModel, SoftDeleteMixin):
    """Salary advances and staff loans recovered via monthly payslips."""

    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="loans",
    )
    loan_type = models.CharField(
        max_length=20,
        choices=LoanType.choices,
        default=LoanType.ADVANCE,
        db_index=True,
    )
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_installment = models.DecimalField(max_digits=12, decimal_places=2)
    total_recovered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.ACTIVE,
        db_index=True,
    )
    disbursed_date = models.DateField(default=timezone.localdate)
    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Staff Loan / Advance"
        verbose_name_plural = "Staff Loans & Advances"
        ordering = ["-disbursed_date", "-created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                check=models.Q(principal_amount__gt=Decimal("0.00")),
                name="staff_loan_principal_positive",
            ),
            models.CheckConstraint(
                check=models.Q(monthly_installment__gt=Decimal("0.00")),
                name="staff_loan_installment_positive",
            ),
            models.CheckConstraint(
                check=models.Q(remaining_balance__gte=Decimal("0.00")),
                name="staff_loan_remaining_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff.employee_id} - {self.get_loan_type_display()} (Remaining: ৳{self.remaining_balance})"


class PayrollRun(TenantOwnedModel, SoftDeleteMixin):
    """Monthly payroll processing batch with period locking and GL reference."""

    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        db_index=True,
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
        db_index=True,
    )
    title = models.CharField(
        max_length=150,
        blank=True,
        help_text="e.g. Salary Sheet - July 2026",
    )
    status = models.CharField(
        max_length=20,
        choices=PayrollRunStatus.choices,
        default=PayrollRunStatus.DRAFT,
        db_index=True,
    )
    is_locked = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Locks the payroll period against any recalculation or modification.",
    )
    working_days_in_month = models.PositiveSmallIntegerField(
        default=26,
        help_text="Total working days in the month used for pro-rata absence calculations.",
    )
    absence_deduction_basis = models.CharField(
        max_length=20,
        choices=AbsenceDeductionBasis.choices,
        default=AbsenceDeductionBasis.BASIC,
    )

    total_gross = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_employer_pf = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payroll_runs",
    )
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prepared_payroll_runs",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_payroll_runs",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_payroll_runs",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Payroll Run"
        verbose_name_plural = "Payroll Runs"
        ordering = ["-year", "-month"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "year", "month"],
                condition=models.Q(is_deleted=False),
                name="unique_active_payroll_run_per_month",
            )
        ]

    def __str__(self) -> str:
        return self.title or f"Payroll {self.year}-{self.month:02d} ({self.status})"


class Payslip(TenantOwnedModel):
    """Individual monthly salary payslip generated within a PayrollRun."""

    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="payslips",
    )

    # Attendance Snapshot (frozen when calculated)
    working_days = models.PositiveSmallIntegerField(default=26)
    present_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    late_days = models.PositiveSmallIntegerField(default=0)
    half_days = models.PositiveSmallIntegerField(default=0)
    paid_leave_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    unpaid_leave_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    absent_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # Monetary Summary (BDT)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    absence_deduction_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    pf_employee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    pf_employer_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    loan_deduction_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Snapshot of disbursement details
    payment_method = models.CharField(
        max_length=20,
        choices=SalaryPaymentMethod.choices,
        default=SalaryPaymentMethod.BANK_TRANSFER,
    )
    is_paid = models.BooleanField(default=False, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Payslip"
        verbose_name_plural = "Payslips"
        ordering = ["staff__employee_id"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["payroll_run", "staff"],
                name="unique_staff_payslip_per_payroll_run",
            ),
            models.CheckConstraint(
                check=models.Q(net_payable__gte=Decimal("0.00")),
                name="payslip_net_payable_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"Payslip: {self.staff.employee_id} ({self.payroll_run.year}-{self.payroll_run.month:02d}) - ৳{self.net_payable}"


class PayslipLine(TenantOwnedModel):
    """Itemized earning or deduction line inside a Payslip."""

    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    component = models.ForeignKey(
        SalaryComponent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    name_en = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True)
    line_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Payslip Line"
        verbose_name_plural = "Payslip Lines"
        ordering = ["line_type", "created_at"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                check=models.Q(amount__gte=Decimal("0.00")),
                name="payslip_line_amount_non_negative",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name_en}: ৳{self.amount}"
