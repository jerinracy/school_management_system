"""Sequential receipt numbering and bilingual PDF receipt generation."""

from django.core.files.base import ContentFile
from django.db import transaction
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.core.pdf.engine import get_bengali_stylesheet, render_story_to_pdf
from apps.fees.models import MoneyReceipt, ReceiptSequence
from apps.institutions.models import Institution


def get_next_receipt_number(institution: Institution, year: int) -> str:
    """Generate the next gap-free sequential money receipt number for an institution and year.

    Format: REC-{year}-{seq:06d}, e.g. REC-2026-000001
    """
    with transaction.atomic():
        seq, _ = ReceiptSequence.objects.select_for_update().get_or_create(
            institution=institution,
            year=year,
            defaults={"last_number": 0},
        )
        seq.last_number += 1
        seq.save(update_fields=["last_number", "updated_at"])

        return f"REC-{year}-{seq.last_number:06d}"


def generate_money_receipt_pdf(receipt: MoneyReceipt) -> bytes:
    """Generate an official bilingual money receipt PDF with Bengali font."""
    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    primary_color = HexColor("#1E3A8A")  # Deep blue
    border_color = HexColor("#E2E8F0")
    header_bg = HexColor("#F1F5F9")
    green_bg = HexColor("#DCFCE7")

    inst = receipt.institution
    student = receipt.student
    payment = receipt.payment
    invoice = payment.invoice

    # 1. Header
    inst_name = f"{inst.name_en} ({inst.name_bn})" if getattr(inst, "name_bn", "") else inst.name_en
    story.append(Paragraph(inst_name, styles["Title"]))

    sub_parts = []
    if getattr(inst, "eiin", ""):
        sub_parts.append(f"EIIN: {inst.eiin}")
    if getattr(inst, "address", ""):
        sub_parts.append(inst.address)
    sub_text = " | ".join(sub_parts) or "School Management System"
    story.append(Paragraph(sub_text, styles["Subtitle"]))
    story.append(Spacer(1, 4))

    # 2. Document Banner
    story.append(Paragraph("MONEY RECEIPT / অর্থ প্রাপ্তি রশিদ", styles["DocHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # 3. Particulars Block
    collector_name = receipt.issued_by.username if receipt.issued_by else "System Online Gateway"
    inv_num = invoice.invoice_number if invoice else "Direct Advance Deposit"

    particulars_data = [
        [
            Paragraph("<b>Receipt No / রশিদ নং:</b>", styles["Body"]),
            Paragraph(f"<b>{receipt.receipt_number}</b>", styles["Body"]),
            Paragraph("<b>Date & Time / তারিখ:</b>", styles["Body"]),
            Paragraph(receipt.issued_at.strftime("%d %b %Y, %I:%M %p"), styles["Body"]),
        ],
        [
            Paragraph("<b>Student Name / নাম:</b>", styles["Body"]),
            Paragraph(f"{student.name_en} ({student.name_bn})", styles["Body"]),
            Paragraph("<b>Student ID / আইডি:</b>", styles["Body"]),
            Paragraph(str(student.student_id), styles["Body"]),
        ],
        [
            Paragraph("<b>Payment Method / মাধ্যম:</b>", styles["Body"]),
            Paragraph(f"<b>{payment.get_payment_method_display()}</b>", styles["Body"]),
            Paragraph("<b>Trx ID / ট্রানজেকশন:</b>", styles["Body"]),
            Paragraph(payment.transaction_id or payment.idempotency_key[:16], styles["Body"]),
        ],
        [
            Paragraph("<b>Invoice Ref / ইনভয়েস:</b>", styles["Body"]),
            Paragraph(inv_num, styles["Body"]),
            Paragraph("<b>Received By / গ্রহণকারী:</b>", styles["Body"]),
            Paragraph(collector_name, styles["Body"]),
        ],
    ]

    t_meta = Table(particulars_data, colWidths=[140, 160, 120, 100])
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

    # 4. Allocations / Items Table
    allocations = list(
        payment.allocations.all().select_related("invoice", "invoice_line__fee_head")
    )
    item_rows = [
        [
            Paragraph("<b>Sl / নং</b>", styles["Body"]),
            Paragraph("<b>Description / বিবরণ</b>", styles["Body"]),
            Paragraph("<b>Invoice / ইনভয়েস</b>", styles["Body"]),
            Paragraph("<b>Paid Amount / টাকা</b>", styles["Body"]),
        ]
    ]

    if not allocations:
        item_rows.append(
            [
                Paragraph("1", styles["Body"]),
                Paragraph("Student Advance Balance Deposit", styles["Body"]),
                Paragraph("N/A (Credit)", styles["Body"]),
                Paragraph(f"৳ {payment.amount:.2f}", styles["Body"]),
            ]
        )
    else:
        for idx, alloc in enumerate(allocations, start=1):
            desc = alloc.invoice_line.description if alloc.invoice_line else alloc.invoice.title
            item_rows.append(
                [
                    Paragraph(str(idx), styles["Body"]),
                    Paragraph(desc, styles["Body"]),
                    Paragraph(alloc.invoice.invoice_number, styles["Body"]),
                    Paragraph(f"৳ {alloc.allocated_amount:.2f}", styles["Body"]),
                ]
            )

    t_items = Table(item_rows, colWidths=[35, 260, 120, 105])
    t_items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_items)
    story.append(Spacer(1, 12))

    # 5. Total Paid Box
    total_data = [
        [
            Paragraph("<b>Total Amount Received / সর্বমোট প্রাপ্ত:</b>", styles["Body"]),
            Paragraph(f"<b>৳ {receipt.total_amount:.2f}</b>", styles["Body"]),
        ]
    ]
    t_total = Table(total_data, colWidths=[200, 120])
    t_total.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), green_bg),
                ("BOX", (0, 0), (-1, -1), 1, primary_color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    outer_total = Table([["", t_total]], colWidths=[200, 320])
    outer_total.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(outer_total)
    story.append(Spacer(1, 40))

    # 6. Signature Lines
    sig_data = [
        [
            Paragraph(
                "____________________________<br/>Depositor / Student Signature", styles["Footer"]
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


def create_or_update_receipt_pdf(receipt: MoneyReceipt) -> MoneyReceipt:
    """Generate PDF for a money receipt and save to model."""
    pdf_bytes = generate_money_receipt_pdf(receipt)
    filename = f"{receipt.receipt_number}.pdf"
    receipt.pdf_receipt.save(filename, ContentFile(pdf_bytes), save=False)
    receipt.save(update_fields=["pdf_receipt", "updated_at"])
    return receipt
