"""DRF Serializers for Payroll Management."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.payroll.models import (
    AbsenceDeductionBasis,
    PayrollRun,
    Payslip,
    PayslipLine,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
    StaffLoan,
    StaffSalaryOverride,
    StaffSalaryProfile,
)


def _assert_same_institution(context: dict[str, Any], obj: Any, field_name: str) -> None:
    """Prevent cross-tenant foreign key references when request user has an institution."""
    request = context.get("request")
    inst_id = getattr(getattr(request, "user", None), "institution_id", None)
    if inst_id and obj is not None and getattr(obj, "institution_id", None) != inst_id:
        raise serializers.ValidationError(
            {field_name: "Referenced record belongs to another institution."}
        )


class SalaryComponentSerializer(serializers.ModelSerializer):
    """Serializer for institutional earning/deduction salary components."""

    class Meta:
        model = SalaryComponent
        fields = [
            "id",
            "code",
            "name_en",
            "name_bn",
            "component_type",
            "calculation_type",
            "default_value",
            "is_taxable",
            "is_system",
            "is_active",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "name" in data:
                if not data.get("name_en"):
                    data["name_en"] = data["name"]
                if not data.get("name_bn"):
                    data["name_bn"] = data["name"]
            if data.get("calculation_type") == "flat":
                data["calculation_type"] = "fixed"
        return super().to_internal_value(data)


class SalaryStructureLineSerializer(serializers.ModelSerializer):
    """Serializer for component lines within a SalaryStructure."""

    component_code = serializers.CharField(source="component.code", read_only=True)
    component_name_en = serializers.CharField(source="component.name_en", read_only=True)
    component_type = serializers.CharField(source="component.component_type", read_only=True)

    class Meta:
        model = SalaryStructureLine
        fields = [
            "id",
            "structure",
            "component",
            "component_code",
            "component_name_en",
            "component_type",
            "calculation_type",
            "value",
        ]
        read_only_fields = ["id", "component_code", "component_name_en", "component_type"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        _assert_same_institution(self.context, attrs.get("structure"), "structure")
        _assert_same_institution(self.context, attrs.get("component"), "component")
        return attrs


class SalaryStructureSerializer(serializers.ModelSerializer):
    """Serializer for reusable salary structure templates."""

    lines = SalaryStructureLineSerializer(many=True, read_only=True)

    class Meta:
        model = SalaryStructure
        fields = [
            "id",
            "code",
            "name",
            "name_bn",
            "description",
            "is_active",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StaffSalaryOverrideSerializer(serializers.ModelSerializer):
    """Serializer for per-employee salary component overrides."""

    component_code = serializers.CharField(source="component.code", read_only=True)
    component_name_en = serializers.CharField(source="component.name_en", read_only=True)

    class Meta:
        model = StaffSalaryOverride
        fields = [
            "id",
            "profile",
            "component",
            "component_code",
            "component_name_en",
            "calculation_type",
            "value",
        ]
        read_only_fields = ["id", "component_code", "component_name_en"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        _assert_same_institution(self.context, attrs.get("profile"), "profile")
        _assert_same_institution(self.context, attrs.get("component"), "component")
        return attrs


class StaffSalaryProfileSerializer(serializers.ModelSerializer):
    """Serializer for staff salary profile, MPO split, PF, and banking details."""

    staff_employee_id = serializers.CharField(source="staff.employee_id", read_only=True)
    staff_name_en = serializers.CharField(source="staff.full_name_en", read_only=True)
    staff_name_bn = serializers.CharField(source="staff.full_name_bn", read_only=True)
    structure_name = serializers.CharField(source="structure.name", read_only=True, default="")
    overrides = StaffSalaryOverrideSerializer(many=True, read_only=True)

    class Meta:
        model = StaffSalaryProfile
        fields = [
            "id",
            "staff",
            "staff_employee_id",
            "staff_name_en",
            "staff_name_bn",
            "structure",
            "structure_name",
            "basic_salary",
            "mpo_portion",
            "institutional_portion",
            "payment_method",
            "bank_name",
            "bank_branch",
            "bank_account_number",
            "bank_routing_number",
            "mfs_number",
            "pf_enrolled",
            "pf_employee_percent",
            "pf_employer_percent",
            "late_deduction_enabled",
            "late_days_per_absent",
            "overtime_hourly_rate",
            "effective_from",
            "is_active",
            "overrides",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "staff_employee_id",
            "staff_name_en",
            "staff_name_bn",
            "structure_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        _assert_same_institution(self.context, attrs.get("staff"), "staff")
        _assert_same_institution(self.context, attrs.get("structure"), "structure")
        return attrs


class StaffLoanSerializer(serializers.ModelSerializer):
    """Serializer for salary advances and staff loans."""

    staff_employee_id = serializers.CharField(source="staff.employee_id", read_only=True)
    staff_name_en = serializers.CharField(source="staff.full_name_en", read_only=True)

    class Meta:
        model = StaffLoan
        fields = [
            "id",
            "staff",
            "staff_employee_id",
            "staff_name_en",
            "loan_type",
            "principal_amount",
            "monthly_installment",
            "total_recovered",
            "remaining_balance",
            "status",
            "disbursed_date",
            "reason",
            "approved_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "staff_employee_id",
            "staff_name_en",
            "total_recovered",
            "remaining_balance",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        _assert_same_institution(self.context, attrs.get("staff"), "staff")
        principal = attrs.get(
            "principal_amount", getattr(self.instance, "principal_amount", Decimal("0.00"))
        )
        installment = attrs.get(
            "monthly_installment", getattr(self.instance, "monthly_installment", Decimal("0.00"))
        )
        if principal <= Decimal("0.00"):
            raise serializers.ValidationError({"principal_amount": "Principal must be positive."})
        if installment <= Decimal("0.00"):
            raise serializers.ValidationError(
                {"monthly_installment": "Monthly installment must be positive."}
            )
        if installment > principal:
            raise serializers.ValidationError(
                {"monthly_installment": "Monthly installment cannot exceed principal amount."}
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> StaffLoan:
        validated_data["remaining_balance"] = validated_data["principal_amount"]
        validated_data["total_recovered"] = Decimal("0.00")
        return super().create(validated_data)


class PayslipLineSerializer(serializers.ModelSerializer):
    """Serializer for itemized earning/deduction rows inside a Payslip."""

    class Meta:
        model = PayslipLine
        fields = [
            "id",
            "component",
            "name_en",
            "name_bn",
            "line_type",
            "amount",
            "notes",
        ]
        read_only_fields = fields


class PayslipSerializer(serializers.ModelSerializer):
    """Serializer for individual employee monthly payslips."""

    staff_employee_id = serializers.CharField(source="staff.employee_id", read_only=True)
    staff_name_en = serializers.CharField(source="staff.full_name_en", read_only=True)
    staff_name_bn = serializers.CharField(source="staff.full_name_bn", read_only=True)
    month = serializers.IntegerField(source="payroll_run.month", read_only=True)
    year = serializers.IntegerField(source="payroll_run.year", read_only=True)
    run_status = serializers.CharField(source="payroll_run.status", read_only=True)
    lines = PayslipLineSerializer(many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id",
            "payroll_run",
            "month",
            "year",
            "run_status",
            "staff",
            "staff_employee_id",
            "staff_name_en",
            "staff_name_bn",
            "working_days",
            "present_days",
            "late_days",
            "half_days",
            "paid_leave_days",
            "unpaid_leave_days",
            "absent_days",
            "overtime_hours",
            "basic_salary",
            "overtime_amount",
            "bonus_amount",
            "gross_earnings",
            "absence_deduction_amount",
            "pf_employee_amount",
            "pf_employer_amount",
            "loan_deduction_amount",
            "total_deductions",
            "net_payable",
            "payment_method",
            "is_paid",
            "paid_at",
            "payment_reference",
            "notes",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PayrollRunSerializer(serializers.ModelSerializer):
    """Serializer for monthly PayrollRun batches."""

    payslips_count = serializers.IntegerField(source="payslips.count", read_only=True)
    journal_entry_voucher_no = serializers.CharField(
        source="journal_entry.voucher_no", read_only=True, default=""
    )

    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "month",
            "year",
            "title",
            "status",
            "is_locked",
            "working_days_in_month",
            "absence_deduction_basis",
            "total_gross",
            "total_deductions",
            "total_net_pay",
            "total_employer_pf",
            "journal_entry",
            "journal_entry_voucher_no",
            "payslips_count",
            "prepared_by",
            "reviewed_by",
            "reviewed_at",
            "approved_by",
            "approved_at",
            "paid_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GeneratePayrollRunSerializer(serializers.Serializer):
    """Input serializer for generating or recalculating a monthly payroll run."""

    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    working_days_in_month = serializers.IntegerField(min_value=1, max_value=31, required=False)
    absence_deduction_basis = serializers.ChoiceField(
        choices=AbsenceDeductionBasis.choices,
        default=AbsenceDeductionBasis.BASIC,
    )
    title = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")


class ApplyBonusSerializer(serializers.Serializer):
    """Input serializer for batch Eid/Festival bonus calculation."""

    bonus_title = serializers.CharField(max_length=150, default="Eid Festival Bonus")
    percentage_of_basic = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    fixed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    staff_type = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")


class MarkPaidSerializer(serializers.Serializer):
    """Input serializer for disbursing an approved payroll run."""

    payment_reference = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


class PostAccountingSerializer(serializers.Serializer):
    """Input serializer for posting a payroll run to apps.accounting GL."""

    posting_date = serializers.DateField(required=False, allow_null=True)
    bank_account_code = serializers.CharField(max_length=50, default="1021")
    cash_account_code = serializers.CharField(max_length=50, default="1010")
    salary_expense_code = serializers.CharField(max_length=50, default="5010")
    liability_account_code = serializers.CharField(max_length=50, default="2030")
