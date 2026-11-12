"""Django admin registrations for Payroll Management."""

from django.contrib import admin

from apps.payroll.models import (
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


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name_en",
        "component_type",
        "calculation_type",
        "default_value",
        "is_active",
        "institution",
    )
    list_filter = ("component_type", "calculation_type", "is_active", "institution")
    search_fields = ("code", "name_en", "name_bn")


class SalaryStructureLineInline(admin.TabularInline):
    model = SalaryStructureLine
    extra = 1


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "institution")
    list_filter = ("is_active", "institution")
    search_fields = ("code", "name", "name_bn")
    inlines = [SalaryStructureLineInline]


class StaffSalaryOverrideInline(admin.TabularInline):
    model = StaffSalaryOverride
    extra = 0


@admin.register(StaffSalaryProfile)
class StaffSalaryProfileAdmin(admin.ModelAdmin):
    list_display = (
        "staff",
        "structure",
        "basic_salary",
        "payment_method",
        "pf_enrolled",
        "is_active",
        "institution",
    )
    list_filter = ("payment_method", "pf_enrolled", "is_active", "institution")
    search_fields = ("staff__employee_id", "staff__full_name_en")
    inlines = [StaffSalaryOverrideInline]


@admin.register(StaffLoan)
class StaffLoanAdmin(admin.ModelAdmin):
    list_display = (
        "staff",
        "loan_type",
        "principal_amount",
        "monthly_installment",
        "remaining_balance",
        "status",
        "institution",
    )
    list_filter = ("loan_type", "status", "institution")
    search_fields = ("staff__employee_id", "staff__full_name_en")


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "year",
        "month",
        "status",
        "is_locked",
        "total_gross",
        "total_deductions",
        "total_net_pay",
        "institution",
    )
    list_filter = ("status", "is_locked", "year", "month", "institution")


class PayslipLineInline(admin.TabularInline):
    model = PayslipLine
    extra = 0
    readonly_fields = ("component", "name_en", "line_type", "amount", "notes")


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        "staff",
        "payroll_run",
        "basic_salary",
        "gross_earnings",
        "total_deductions",
        "net_payable",
        "is_paid",
    )
    list_filter = ("is_paid", "payment_method", "payroll_run")
    search_fields = ("staff__employee_id", "staff__full_name_en")
    inlines = [PayslipLineInline]
