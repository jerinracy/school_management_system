"""BEFTN / Bank Advice sheet exports (XLSX and CSV) for monthly payroll runs."""

import calendar
import csv
import io
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from apps.payroll.models import PayrollRun, SalaryPaymentMethod

BANK_ADVICE_HEADERS = [
    "Sl",
    "Employee ID",
    "Employee Name",
    "Department",
    "Designation",
    "Payment Method",
    "Bank Name",
    "Branch",
    "Account Number / MFS No",
    "Routing Number",
    "Net Payable (BDT)",
]


def _collect_advice_rows(
    payroll_run: PayrollRun,
    payment_method: str | None = None,
) -> list[dict[str, Any]]:
    """Collect BEFTN / disbursement rows ordered by employee ID without exposing raw secrets in logs."""
    payslips = (
        payroll_run.payslips.select_related(
            "staff",
            "staff__department",
            "staff__designation",
            "staff__salary_profile",
        )
        .filter(net_payable__gt=Decimal("0.00"))
        .order_by("staff__employee_id")
    )
    if payment_method:
        payslips = payslips.filter(payment_method=payment_method)

    rows: list[dict[str, Any]] = []
    for idx, slip in enumerate(payslips, start=1):
        staff = slip.staff
        profile = getattr(staff, "salary_profile", None)
        account_or_mfs = ""
        bank_name = ""
        bank_branch = ""
        routing = ""
        if profile is not None:
            bank_name = profile.bank_name
            bank_branch = profile.bank_branch
            routing = profile.bank_routing_number
            account_or_mfs = (
                profile.mfs_number
                if slip.payment_method == SalaryPaymentMethod.MFS and profile.mfs_number
                else profile.bank_account_number
            )

        rows.append(
            {
                "sl": idx,
                "employee_id": staff.employee_id,
                "employee_name": staff.full_name_en,
                "department": staff.department.name if staff.department else "",
                "designation": staff.designation.title if staff.designation else "",
                "payment_method": slip.get_payment_method_display(),
                "bank_name": bank_name,
                "bank_branch": bank_branch,
                "account_number": account_or_mfs,
                "routing_number": routing,
                "net_payable": slip.net_payable,
            }
        )
    return rows


def export_bank_advice_csv(
    payroll_run: PayrollRun,
    payment_method: str | None = None,
) -> bytes:
    """Export BEFTN / bank advice sheet in UTF-8 CSV format."""
    rows = _collect_advice_rows(payroll_run, payment_method=payment_method)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(BANK_ADVICE_HEADERS)

    total_net = Decimal("0.00")
    for r in rows:
        total_net += r["net_payable"]
        writer.writerow(
            [
                r["sl"],
                r["employee_id"],
                r["employee_name"],
                r["department"],
                r["designation"],
                r["payment_method"],
                r["bank_name"],
                r["bank_branch"],
                r["account_number"],
                r["routing_number"],
                f"{r['net_payable']:.2f}",
            ]
        )

    writer.writerow(["", "", "TOTAL", "", "", "", "", "", "", "", f"{total_net:.2f}"])
    return buf.getvalue().encode("utf-8-sig")


def export_bank_advice_xlsx(
    payroll_run: PayrollRun,
    payment_method: str | None = None,
) -> bytes:
    """Export formatted BEFTN / bank transfer advice workbook (.xlsx) using openpyxl."""
    rows = _collect_advice_rows(payroll_run, payment_method=payment_method)
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Bank Advice"

    inst = payroll_run.institution
    month_name = calendar.month_name[payroll_run.month]

    ws.merge_cells("A1:K1")
    ws["A1"] = f"{inst.name_en} — Salary Bank Advice ({month_name} {payroll_run.year})"
    ws["A1"].font = Font(bold=True, size=13, color="1B365D")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.append(BANK_ADVICE_HEADERS)
    header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for col_idx in range(1, len(BANK_ADVICE_HEADERS) + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    total_net = Decimal("0.00")
    for r in rows:
        total_net += r["net_payable"]
        ws.append(
            [
                r["sl"],
                r["employee_id"],
                r["employee_name"],
                r["department"],
                r["designation"],
                r["payment_method"],
                r["bank_name"],
                r["bank_branch"],
                r["account_number"],
                r["routing_number"],
                float(r["net_payable"]),
            ]
        )
        ws.cell(row=ws.max_row, column=11).number_format = "#,##0.00"

    ws.append(["", "", "TOTAL", "", "", "", "", "", "", "", float(total_net)])
    total_row = ws.max_row
    ws.cell(row=total_row, column=3).font = Font(bold=True)
    ws.cell(row=total_row, column=11).font = Font(bold=True)
    ws.cell(row=total_row, column=11).number_format = "#,##0.00"

    widths = [6, 15, 26, 18, 20, 22, 22, 18, 22, 16, 18]
    for col_idx, width in enumerate(widths, start=1):
        col_letter = ws.cell(row=2, column=col_idx).column_letter
        ws.column_dimensions[col_letter].width = width

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
