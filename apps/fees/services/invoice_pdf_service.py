"""Bilingual invoice & fee payment receipt PDF generation with Bengali font."""

from django.core.files.base import ContentFile
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.core.pdf.engine import get_bengali_stylesheet, render_story_to_pdf
from apps.fees.models import Invoice


def generate_invoice_pdf(invoice: Invoice) -> bytes:
    """Generate a bilingual (Bangla & English) fee demand & receipt slip."""
    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    primary_color = HexColor("#1E3A8A")  # Deep blue
    border_color = HexColor("#E2E8F0")  # Slate 200
    header_bg = HexColor("#F1F5F9")  # Slate 100
    green_bg = HexColor("#DCFCE7")  # Soft green
    red_bg = HexColor("#FEE2E2")  # Soft red

    inst = invoice.institution
    student = invoice.student
    enrollment = invoice.enrollment

    # 1. Institution Header
    inst_name_display = (
        f"{inst.name_en} ({inst.name_bn})" if getattr(inst, "name_bn", "") else inst.name_en
    )
    story.append(Paragraph(inst_name_display, styles["Title"]))

    sub_parts = []
    if getattr(inst, "eiin", ""):
        sub_parts.append(f"EIIN: {inst.eiin}")
    if getattr(inst, "address", ""):
        sub_parts.append(inst.address)
    sub_text = " | ".join(sub_parts) or "School Management System"
    story.append(Paragraph(sub_text, styles["Subtitle"]))
    story.append(Spacer(1, 4))

    # 2. Document Title Banner
    badge_title = invoice.title or f"FEE DEMAND INVOICE - {invoice.session.name}"
    story.append(Paragraph(badge_title.upper(), styles["DocHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # 3. Invoice & Student Particulars Block (2-column layout)
    sec_name = enrollment.section.name if (enrollment and enrollment.section) else "N/A"
    cls_name = enrollment.class_level.name if (enrollment and enrollment.class_level) else "N/A"
    roll_no = enrollment.roll_no if enrollment else "N/A"
    shift_name = enrollment.shift.name if (enrollment and enrollment.shift) else "Morning/Day"

    student_data = [
        [
            Paragraph("<b>Student Name / শিক্ষার্থীর নাম:</b>", styles["Body"]),
            Paragraph(f"{student.name_en} ({student.name_bn})", styles["Body"]),
            Paragraph("<b>Invoice No / ইনভয়েস নং:</b>", styles["Body"]),
            Paragraph(f"<b>{invoice.invoice_number}</b>", styles["Body"]),
        ],
        [
            Paragraph("<b>Student ID / আইডি:</b>", styles["Body"]),
            Paragraph(str(student.student_id), styles["Body"]),
            Paragraph("<b>Status / অবস্থা:</b>", styles["Body"]),
            Paragraph(invoice.status.upper(), styles["Body"]),
        ],
        [
            Paragraph("<b>Class & Section / শ্রেণী ও শাখা:</b>", styles["Body"]),
            Paragraph(f"{cls_name} - {sec_name} (Roll: {roll_no})", styles["Body"]),
            Paragraph("<b>Issue Date / ইস্যুর তারিখ:</b>", styles["Body"]),
            Paragraph(invoice.issue_date.strftime("%d %b %Y"), styles["Body"]),
        ],
        [
            Paragraph("<b>Shift / শিফট:</b>", styles["Body"]),
            Paragraph(shift_name, styles["Body"]),
            Paragraph("<b>Due Date / শেষ তারিখ:</b>", styles["Body"]),
            Paragraph(invoice.due_date.strftime("%d %b %Y"), styles["Body"]),
        ],
    ]

    t_meta = Table(student_data, colWidths=[150, 160, 110, 100])
    t_meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ]
        )
    )
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # 4. Itemized Fee Breakdown Table
    item_rows = [
        [
            Paragraph("<b>Sl / নং</b>", styles["Body"]),
            Paragraph("<b>Fee Head / ফি বিবরণ</b>", styles["Body"]),
            Paragraph("<b>Original (৳)</b>", styles["Body"]),
            Paragraph("<b>Waiver (৳)</b>", styles["Body"]),
            Paragraph("<b>Payable (৳)</b>", styles["Body"]),
        ]
    ]

    lines = list(invoice.lines.all().select_related("fee_head"))
    if not lines:
        item_rows.append(
            [
                Paragraph("1", styles["Body"]),
                Paragraph(invoice.title or "Consolidated Tuition Fee", styles["Body"]),
                Paragraph(f"{invoice.subtotal_amount:.2f}", styles["Body"]),
                Paragraph(f"{invoice.waiver_amount:.2f}", styles["Body"]),
                Paragraph(f"{invoice.total_payable:.2f}", styles["Body"]),
            ]
        )
    else:
        for idx, line in enumerate(lines, start=1):
            item_rows.append(
                [
                    Paragraph(str(idx), styles["Body"]),
                    Paragraph(line.description, styles["Body"]),
                    Paragraph(f"{line.amount:.2f}", styles["Body"]),
                    Paragraph(f"{line.waiver_amount:.2f}", styles["Body"]),
                    Paragraph(f"<b>{line.payable_amount:.2f}</b>", styles["Body"]),
                ]
            )

    t_items = Table(item_rows, colWidths=[35, 235, 80, 80, 90])
    t_items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_items)
    story.append(Spacer(1, 10))

    # 5. Financial Summary Box (Right aligned)
    status_bg = (
        green_bg
        if invoice.status == "paid"
        else (red_bg if invoice.status == "overdue" else header_bg)
    )
    summary_data = [
        [
            Paragraph("<b>Subtotal / মোট ফি:</b>", styles["Body"]),
            Paragraph(f"৳ {invoice.subtotal_amount:.2f}", styles["Body"]),
        ],
        [
            Paragraph("<b>Total Waiver / মওকুফ:</b>", styles["Body"]),
            Paragraph(f"- ৳ {invoice.waiver_amount:.2f}", styles["Body"]),
        ],
        [
            Paragraph("<b>Late Fine / বিলম্ব ফি:</b>", styles["Body"]),
            Paragraph(f"+ ৳ {invoice.fine_amount:.2f}", styles["Body"]),
        ],
        [
            Paragraph("<b>Total Payable / প্রদেয় মোট:</b>", styles["Body"]),
            Paragraph(f"<b>৳ {invoice.total_payable:.2f}</b>", styles["Body"]),
        ],
        [
            Paragraph("<b>Paid Amount / পরিশোধিত:</b>", styles["Body"]),
            Paragraph(f"৳ {invoice.paid_amount:.2f}", styles["Body"]),
        ],
        [
            Paragraph("<b>Due Balance / বকেয়া টাকা:</b>", styles["Body"]),
            Paragraph(f"<b>৳ {invoice.due_amount:.2f}</b>", styles["Body"]),
        ],
    ]

    t_summary = Table(summary_data, colWidths=[140, 110])
    t_summary.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("BACKGROUND", (0, 3), (1, 3), header_bg),
                ("BACKGROUND", (0, 5), (1, 5), status_bg),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    # Wrap summary in an outer table to align right
    outer_wrapper = Table([["", t_summary]], colWidths=[270, 250])
    outer_wrapper.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(outer_wrapper)
    story.append(Spacer(1, 25))

    # 6. Payment Instructions & Signatures
    story.append(
        Paragraph(
            "<b>Instructions:</b> Please pay before the due date to avoid late fees. Payments can be made via authorized bank counters or official online portal (bKash/Nagad/Cards).",
            styles["Body"],
        )
    )
    story.append(Spacer(1, 35))

    sig_data = [
        [
            Paragraph(
                "____________________________<br/>Student / Guardian Signature", styles["Footer"]
            ),
            Paragraph(
                "____________________________<br/>Cashier / Accounts Officer", styles["Footer"]
            ),
            Paragraph(
                "____________________________<br/>Principal / Head of Institution", styles["Footer"]
            ),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[173, 173, 174])
    t_sig.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(t_sig)

    return render_story_to_pdf(story=story, pagesize=A4, margin=36.0)


def create_or_update_invoice_pdf(invoice: Invoice) -> Invoice:
    """Generate PDF for an invoice and save to FileField."""
    pdf_bytes = generate_invoice_pdf(invoice)
    filename = f"{invoice.invoice_number}.pdf"
    invoice.pdf_receipt.save(filename, ContentFile(pdf_bytes), save=False)
    invoice.save(update_fields=["pdf_receipt", "updated_at"])
    return invoice
