"""Bilingual (Bangla & English) Monthly Payslip PDF generation service."""

import calendar

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.accounting.services.voucher_pdf_service import number_to_words_bdt
from apps.core.pdf.engine import (
    ensure_bengali_fonts_registered,
    get_bengali_stylesheet,
    render_story_to_pdf,
)
from apps.payroll.models import ComponentType, Payslip


def render_payslip_pdf(payslip: Payslip) -> bytes:
    """Render an official bilingual monthly Payslip PDF with attendance and itemized breakdown."""
    font_name = ensure_bengali_fonts_registered()
    styles = get_bengali_stylesheet()
    inst = payslip.institution
    run = payslip.payroll_run
    staff = payslip.staff

    th_style = ParagraphStyle(
        "PayslipTH",
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=HexColor("#FFFFFF"),
        alignment=TA_LEFT,
    )
    th_right = ParagraphStyle(
        "PayslipTHRight",
        parent=th_style,
        alignment=TA_RIGHT,
    )
    cell_style = ParagraphStyle(
        "PayslipCell",
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=HexColor("#1F2937"),
        alignment=TA_LEFT,
    )
    cell_right = ParagraphStyle(
        "PayslipCellRight",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    story: list[Flowable] = []

    # Institution Header
    story.append(Paragraph(inst.name_en, styles["Title"]))
    if inst.name_bn:
        story.append(Paragraph(inst.name_bn, styles["Subtitle"]))

    meta_parts = []
    if getattr(inst, "address", ""):
        meta_parts.append(inst.address)
    if getattr(inst, "eiin", ""):
        meta_parts.append(f"EIIN: {inst.eiin}")
    if meta_parts:
        story.append(Paragraph(" | ".join(meta_parts), styles["Subtitle"]))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1B365D")))
    story.append(Spacer(1, 6))

    month_name = calendar.month_name[run.month]
    story.append(
        Paragraph(
            f"PAYSLIP / বেতন স্লিপ — {month_name} {run.year}",
            styles["DocHeader"],
        )
    )
    story.append(Spacer(1, 6))

    # Staff & Attendance Summary Table
    dept_name = staff.department.name if staff.department else "N/A"
    desig_name = staff.designation.title if staff.designation else "N/A"
    staff_name = staff.full_name_en + (f" ({staff.full_name_bn})" if staff.full_name_bn else "")

    info_rows = [
        [
            Paragraph("<b>Employee ID:</b>", styles["Label"]),
            Paragraph(staff.employee_id, styles["Value"]),
            Paragraph("<b>Salary Period:</b>", styles["Label"]),
            Paragraph(f"{month_name} {run.year}", styles["Value"]),
        ],
        [
            Paragraph("<b>Employee Name:</b>", styles["Label"]),
            Paragraph(staff_name, styles["Value"]),
            Paragraph("<b>Payment Status:</b>", styles["Label"]),
            Paragraph("Paid" if payslip.is_paid else run.get_status_display(), styles["Value"]),
        ],
        [
            Paragraph("<b>Department:</b>", styles["Label"]),
            Paragraph(dept_name, styles["Value"]),
            Paragraph("<b>Designation:</b>", styles["Label"]),
            Paragraph(desig_name, styles["Value"]),
        ],
        [
            Paragraph("<b>Working Days:</b>", styles["Label"]),
            Paragraph(
                f"{payslip.working_days} (Present: {payslip.present_days}, Late: {payslip.late_days})",
                styles["Value"],
            ),
            Paragraph("<b>Leave / Absent:</b>", styles["Label"]),
            Paragraph(
                f"Paid Leave: {payslip.paid_leave_days}, Unpaid: {payslip.unpaid_leave_days}, Absent: {payslip.absent_days}",
                styles["Value"],
            ),
        ],
    ]
    info_table = Table(info_rows, colWidths=[90, 175, 95, 160])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.75, HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 10))

    # Side-by-side Earnings & Deductions Lines
    lines = list(payslip.lines.all())
    earnings = [ln for ln in lines if ln.line_type == ComponentType.EARNING]
    deductions = [ln for ln in lines if ln.line_type == ComponentType.DEDUCTION]
    max_rows = max(len(earnings), len(deductions), 1)

    item_rows: list[list[Flowable]] = [
        [
            Paragraph("Earnings (আয়সমূহ)", th_style),
            Paragraph("Amount (BDT)", th_right),
            Paragraph("Deductions (কর্তনসমূহ)", th_style),
            Paragraph("Amount (BDT)", th_right),
        ]
    ]

    for idx in range(max_rows):
        if idx < len(earnings):
            e = earnings[idx]
            e_label = e.name_en + (f" ({e.name_bn})" if e.name_bn else "")
            e_cell = Paragraph(e_label, cell_style)
            e_amt = Paragraph(f"৳{e.amount:,.2f}", cell_right)
        else:
            e_cell = Paragraph("", cell_style)
            e_amt = Paragraph("", cell_right)

        if idx < len(deductions):
            d = deductions[idx]
            d_label = d.name_en + (f" ({d.name_bn})" if d.name_bn else "")
            d_cell = Paragraph(d_label, cell_style)
            d_amt = Paragraph(f"৳{d.amount:,.2f}", cell_right)
        else:
            d_cell = Paragraph("", cell_style)
            d_amt = Paragraph("", cell_right)

        item_rows.append([e_cell, e_amt, d_cell, d_amt])

    item_rows.append(
        [
            Paragraph("<b>Gross Earnings (মোট আয়)</b>", cell_style),
            Paragraph(f"<b>৳{payslip.gross_earnings:,.2f}</b>", cell_right),
            Paragraph("<b>Total Deductions (মোট কর্তন)</b>", cell_style),
            Paragraph(f"<b>৳{payslip.total_deductions:,.2f}</b>", cell_right),
        ]
    )

    items_table = Table(item_rows, colWidths=[175, 85, 175, 85])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1B365D")),
                ("BACKGROUND", (0, -1), (-1, -1), HexColor("#EEF2FF")),
                ("BOX", (0, 0), (-1, -1), 0.75, HexColor("#94A3B8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Net Pay Summary Box
    words = number_to_words_bdt(payslip.net_payable)
    summary_rows = [
        [
            Paragraph("<b>Net Payable Salary (নীট প্রদেয় বেতন):</b>", styles["Label"]),
            Paragraph(f"<b>BDT ৳{payslip.net_payable:,.2f}</b>", cell_right),
        ],
        [
            Paragraph("<b>In Words:</b>", styles["Label"]),
            Paragraph(words, styles["Value"]),
        ],
        [
            Paragraph("<b>Payment Method / Employer PF:</b>", styles["Label"]),
            Paragraph(
                f"{payslip.get_payment_method_display()} | Employer PF Contribution: ৳{payslip.pf_employer_amount:,.2f}",
                styles["Value"],
            ),
        ],
    ]
    summary_table = Table(summary_rows, colWidths=[190, 330])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#ECFDF5")),
                ("BOX", (0, 0), (-1, -1), 0.75, HexColor("#10B981")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, HexColor("#D1FAE5")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 24))

    # Signatures
    sig_table = Table(
        [
            [
                Paragraph("________________________<br/>Employee Signature", styles["Body"]),
                Paragraph("________________________<br/>Accounts Officer", styles["Body"]),
                Paragraph("________________________<br/>Head of Institution", styles["Body"]),
            ]
        ],
        colWidths=[173, 173, 174],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ]
        )
    )
    story.append(sig_table)
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"Generated digitally by School Management System | Payslip Ref: {str(payslip.id)[:8].upper()}",
            styles["Footer"],
        )
    )

    return render_story_to_pdf(story)
