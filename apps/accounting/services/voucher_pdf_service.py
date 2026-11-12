"""Official accounting voucher PDF generation service with bilingual support."""

from decimal import Decimal

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.accounting.models import JournalEntry
from apps.core.pdf.engine import (
    ensure_bengali_fonts_registered,
    get_bengali_stylesheet,
    render_story_to_pdf,
)

VOUCHER_TYPE_NAMES = {
    "PV": ("PAYMENT VOUCHER", "ডেবিট / খরচ ভাউচার"),
    "payment": ("PAYMENT VOUCHER", "ডেবিট / খরচ ভাউচার"),
    "RV": ("RECEIPT VOUCHER", "ক্রেডিট / জমা ভাউচার"),
    "receipt": ("RECEIPT VOUCHER", "ক্রেডিট / জমা ভাউচার"),
    "JV": ("JOURNAL VOUCHER", "সাধারণ সমন্বয় ভাউচার"),
    "journal": ("JOURNAL VOUCHER", "সাধারণ সমন্বয় ভাউচার"),
    "CV": ("CONTRA VOUCHER", "বিপরীত ভাউচার (কন্ট্রা)"),
    "contra": ("CONTRA VOUCHER", "বিপরীত ভাউচার (কন্ট্রা)"),
}


def number_to_words_bdt(amount: Decimal) -> str:
    """Simple converter for BDT amount to words."""
    try:
        total = int(amount)
        poisha = int(round((amount - total) * 100))

        def chunk_words(n: int) -> str:
            units = [
                "",
                "One",
                "Two",
                "Three",
                "Four",
                "Five",
                "Six",
                "Seven",
                "Eight",
                "Nine",
                "Ten",
                "Eleven",
                "Twelve",
                "Thirteen",
                "Fourteen",
                "Fifteen",
                "Sixteen",
                "Seventeen",
                "Eighteen",
                "Nineteen",
            ]
            tens = [
                "",
                "",
                "Twenty",
                "Thirty",
                "Forty",
                "Fifty",
                "Sixty",
                "Seventy",
                "Eighty",
                "Ninety",
            ]
            if n == 0:
                return ""
            elif n < 20:
                return units[n]
            elif n < 100:
                return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
            elif n < 1000:
                return (
                    units[n // 100]
                    + " Hundred"
                    + (" " + chunk_words(n % 100) if n % 100 != 0 else "")
                )
            elif n < 100000:  # Bangladeshi numbering: Thousand
                return (
                    chunk_words(n // 1000)
                    + " Thousand"
                    + (" " + chunk_words(n % 1000) if n % 1000 != 0 else "")
                )
            elif n < 10000000:  # Bangladeshi numbering: Lakh (100,000)
                return (
                    chunk_words(n // 100000)
                    + " Lakh"
                    + (" " + chunk_words(n % 100000) if n % 100000 != 0 else "")
                )
            else:  # Bangladeshi numbering: Crore (10,000,000)
                return (
                    chunk_words(n // 10000000)
                    + " Crore"
                    + (" " + chunk_words(n % 10000000) if n % 10000000 != 0 else "")
                )

        words = chunk_words(total) or "Zero"
        res = f"{words} Taka"
        if poisha > 0:
            res += f" and {chunk_words(poisha)} Poisha"
        return res + " Only"
    except Exception:
        return f"{amount} Taka Only"


def generate_voucher_pdf(entry: JournalEntry) -> bytes:
    """Generate an official bilingual printable voucher PDF."""
    styles = get_bengali_stylesheet()
    font_name = ensure_bengali_fonts_registered()
    story: list[Flowable] = []

    primary_color = HexColor("#0F172A")  # Slate 900
    border_color = HexColor("#CBD5E1")  # Slate 300
    header_bg = HexColor("#F1F5F9")  # Slate 100

    th_style = ParagraphStyle(
        "VoucherTH", parent=styles["Body"], fontName=font_name, fontSize=9, leading=12, alignment=1
    )
    tb_style = ParagraphStyle(
        "VoucherTB", parent=styles["Body"], fontName=font_name, fontSize=9, leading=12
    )
    tb_center = ParagraphStyle("VoucherTBC", parent=tb_style, alignment=1)
    tb_right = ParagraphStyle("VoucherTBR", parent=tb_style, alignment=2)

    inst = entry.institution
    v_en, v_bn = VOUCHER_TYPE_NAMES.get(entry.voucher_type, ("ACCOUNTING VOUCHER", "হিসাব ভাউচার"))

    # 1. Institution Header
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
    banner_text = f"<b>{v_en} / {v_bn}</b>"
    story.append(Paragraph(banner_text, styles["DocHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # 3. Voucher Meta Table
    status_label = entry.status.upper()
    meta_data = [
        [
            Paragraph("<b>Voucher No / ভাউচার নং:</b>", styles["Body"]),
            Paragraph(f"<b>{entry.voucher_no}</b>", styles["Body"]),
            Paragraph("<b>Date / তারিখ:</b>", styles["Body"]),
            Paragraph(str(entry.date), styles["Body"]),
        ],
        [
            Paragraph("<b>Fiscal Year / অর্থবছর:</b>", styles["Body"]),
            Paragraph(entry.fiscal_year.name if entry.fiscal_year else "-", styles["Body"]),
            Paragraph("<b>Status / অবস্থা:</b>", styles["Body"]),
            Paragraph(f"<b>{status_label}</b>", styles["Body"]),
        ],
    ]
    if entry.cheque_no or entry.payment_reference:
        ref_str = (
            (entry.payment_reference.transaction_id or str(entry.payment_reference.id)[:8])
            if entry.payment_reference
            else "-"
        )
        meta_data.append(
            [
                Paragraph("<b>Cheque No / চেক নং:</b>", styles["Body"]),
                Paragraph(entry.cheque_no or "-", styles["Body"]),
                Paragraph("<b>Ref / রেফারেন্স:</b>", styles["Body"]),
                Paragraph(ref_str, styles["Body"]),
            ]
        )

    meta_table = Table(meta_data, colWidths=[120, 160, 100, 140])
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 4. Line Items Table
    items = entry.items.select_related("account").all().order_by("created_at")
    table_data = [
        [
            Paragraph("<b>#</b>", th_style),
            Paragraph("<b>Account Code & Head / হিসাবের নাম</b>", th_style),
            Paragraph("<b>Particulars / বিবরণ</b>", th_style),
            Paragraph("<b>Debit (৳) / ডেবিট</b>", th_style),
            Paragraph("<b>Credit (৳) / ক্রেডিট</b>", th_style),
        ]
    ]

    for idx, item in enumerate(items, start=1):
        acct_label = f"[{item.account.account_code}] {item.account.name_en}"
        if item.account.name_bn:
            acct_label += f"<br/>{item.account.name_bn}"
        debit_str = f"৳{item.debit:,.2f}" if item.debit > 0 else "-"
        credit_str = f"৳{item.credit:,.2f}" if item.credit > 0 else "-"
        item_narration = item.narration or "-"

        table_data.append(
            [
                Paragraph(str(idx), tb_center),
                Paragraph(acct_label, tb_style),
                Paragraph(item_narration, tb_style),
                Paragraph(debit_str, tb_right),
                Paragraph(credit_str, tb_right),
            ]
        )

    # Total Row
    table_data.append(
        [
            Paragraph("", tb_style),
            Paragraph("<b>Total / সর্বমোট:</b>", tb_style),
            Paragraph("", tb_style),
            Paragraph(f"<b>৳{entry.total_debit:,.2f}</b>", tb_right),
            Paragraph(f"<b>৳{entry.total_credit:,.2f}</b>", tb_right),
        ]
    )

    item_table = Table(table_data, colWidths=[25, 200, 135, 80, 80])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, primary_color),
                ("LINEABOVE", (0, -1), (-1, -1), 1.2, primary_color),
                ("BACKGROUND", (0, -1), (-1, -1), header_bg),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 8))

    # 5. Narration and Amount in Words
    words = number_to_words_bdt(entry.total_debit)
    details_data = [
        [
            Paragraph("<b>In Words / কথায়:</b>", styles["Body"]),
            Paragraph(f"<b>{words}</b>", styles["Body"]),
        ],
        [
            Paragraph("<b>Narration / ব্যাখ্যা:</b>", styles["Body"]),
            Paragraph(entry.narration or "N/A", styles["Body"]),
        ],
    ]
    details_table = Table(details_data, colWidths=[110, 410])
    details_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 40))

    # 6. Signatures block
    sig_data = [
        [
            Paragraph("___________________<br/><b>Prepared By</b><br/>প্রস্তুতকারী", tb_center),
            Paragraph("___________________<br/><b>Checked By</b><br/>নিরীক্ষক", tb_center),
            Paragraph("___________________<br/><b>Accountant</b><br/>হিসাবরক্ষক", tb_center),
            Paragraph(
                "___________________<br/><b>Principal / Head</b><br/>অধ্যক্ষ / প্রধান শিক্ষক", tb_center
            ),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[130, 130, 130, 130])
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(sig_table)

    return render_story_to_pdf(story)
