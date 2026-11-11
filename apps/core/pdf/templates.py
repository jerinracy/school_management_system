"""Document templates for Bengali school certificates, testimonials, and ID cards."""

from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.core.pdf.engine import get_bengali_stylesheet, render_story_to_pdf
from apps.core.utils.bangla import to_bangla_digits


def generate_transfer_certificate_pdf(
    institution_data: dict[str, Any],
    student_data: dict[str, Any],
    enrollment_data: dict[str, Any],
    tc_data: dict[str, Any],
) -> bytes:
    """Generate official Bangladeshi School Transfer Certificate (ছাড়পত্র) PDF.

    Includes bilingual header, student particulars, academic standing, and clearance seal.
    """
    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    # 1. Institution Header
    inst_name_bn = institution_data.get("name_bn") or institution_data.get("name", "বিদ্যালয়")
    inst_name_en = institution_data.get("name_en") or institution_data.get("name", "School")
    eiin = institution_data.get("eiin", "")
    address = institution_data.get("address", "")
    contact_phone = institution_data.get("phone", "")

    story.append(Paragraph(f"<b>{inst_name_bn}</b>", styles["Title"]))
    story.append(Paragraph(f"{inst_name_en}", styles["Subtitle"]))
    subtext = f"EIIN: {eiin} | ঠিকানা: {address}" if eiin else f"ঠিকানা: {address}"
    if contact_phone:
        subtext += f" | ফোন: {contact_phone}"
    story.append(Paragraph(subtext, styles["Footer"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1E3A8A"), spaceAfter=12))

    # 2. Document Title
    story.append(Paragraph("<b>ছাড়পত্র / TRANSFER CERTIFICATE</b>", styles["DocHeader"]))

    # 3. Meta: TC No & Date
    tc_number = tc_data.get("tc_number", "TC-DRAFT")
    issue_date = str(tc_data.get("issue_date", ""))
    meta_table_data = [
        [
            Paragraph(f"<b>স্মারক নং / TC No:</b> {tc_number}", styles["Body"]),
            Paragraph(f"<b>তারিখ / Date:</b> {issue_date}", styles["Body"]),
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 4. Certification Statement
    statement = (
        "এই মর্মে প্রত্যয়ন করা যাচ্ছে যে, নিম্নবর্ণিত শিক্ষার্থী অত্র বিদ্যালয়ের নিয়মিত ছাত্র/ছাত্রী ছিল। "
        "আবেদনক্রমে তাহাকে এই ছাড়পত্র প্রদান করা হলো।"
    )
    story.append(Paragraph(statement, styles["Body"]))
    story.append(Spacer(1, 10))

    # 5. Student Details Table
    details = [
        ("শিক্ষার্থীর নাম (বাংলা)", student_data.get("name_bn", "")),
        ("Student Name (English)", student_data.get("name_en", "")),
        ("শিক্ষার্থী পরিচিতি নং (ID)", student_data.get("student_id", "")),
        ("শ্রেণি (Class)", enrollment_data.get("class_name", "")),
        ("শাখা (Section)", enrollment_data.get("section_name", "")),
        (
            "শ্রেণি রোল (Roll No)",
            str(enrollment_data.get("roll_no", ""))
            + f" ({to_bangla_digits(enrollment_data.get('roll_no', ''))})",
        ),
        ("শিক্ষা বর্ষ (Session)", enrollment_data.get("session_name", "")),
        ("জন্ম তারিখ (Date of Birth)", str(student_data.get("dob", ""))),
        ("জন্ম নিবন্ধন নং (Birth Reg No)", student_data.get("birth_reg_no", "প্রযোজ্য নয়")),
        ("ছাড়পত্রের কারণ (Reason)", tc_data.get("reason", "অভিভাবকের বদলি / বাসস্থান পরিবর্তন")),
        ("আচরণ ও স্বভাব (Conduct)", tc_data.get("conduct_remarks", "উত্তম ও সন্তোষজনক")),
        (
            "আর্থিক অবস্থা (Dues)",
            "সকল বকেয়া পাওনা পরিশোধিত" if tc_data.get("dues_cleared", True) else "বকেয়া বিদ্যমান",
        ),
    ]

    table_data = [
        [
            Paragraph(f"<b>{label}</b>", styles["Label"]),
            Paragraph(f": {val}", styles["Value"]),
        ]
        for label, val in details
    ]

    details_table = Table(table_data, colWidths=[2.6 * inch, 4.5 * inch])
    details_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 30))

    # 6. Well Wishes & Clearance note
    closing = (
        "তাহার ভবিষ্যৎ জীবনের সর্বাঙ্গীন মঙ্গল ও সাফল্য কামনা করি। অত্র বিদ্যালয়ে অধ্যয়নকালে সে কোনো "
        "বিদ্যালয়-বিরোধী কার্যকলাপে লিপ্ত ছিল না।"
    )
    story.append(Paragraph(closing, styles["Body"]))
    story.append(Spacer(1, 60))

    # 7. Signature Line
    sig_data = [
        [
            Paragraph("______________________<br/>শ্রেণি শিক্ষকের স্বাক্ষর", styles["Footer"]),
            Paragraph("______________________<br/>অফিস সহকারী", styles["Footer"]),
            Paragraph("______________________<br/><b>প্রধান শিক্ষক / অধ্যক্ষ</b>", styles["Footer"]),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[2.3 * inch, 2.3 * inch, 2.4 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(sig_table)

    return render_story_to_pdf(story, pagesize=A4, margin=36.0)


def generate_testimonial_pdf(
    institution_data: dict[str, Any],
    student_data: dict[str, Any],
    enrollment_data: dict[str, Any],
    testimonial_data: dict[str, Any],
) -> bytes:
    """Generate official Bangladeshi School Testimonial / Character Certificate (প্রশংসাপত্র) PDF."""
    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    # 1. Institution Header
    inst_name_bn = institution_data.get("name_bn") or institution_data.get("name", "বিদ্যালয়")
    inst_name_en = institution_data.get("name_en") or institution_data.get("name", "School")
    eiin = institution_data.get("eiin", "")
    address = institution_data.get("address", "")

    story.append(Paragraph(f"<b>{inst_name_bn}</b>", styles["Title"]))
    story.append(Paragraph(f"{inst_name_en}", styles["Subtitle"]))
    subtext = f"EIIN: {eiin} | {address}" if eiin else address
    story.append(Paragraph(subtext, styles["Footer"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1E3A8A"), spaceAfter=12))

    # 2. Document Title
    story.append(Paragraph("<b>প্রশংসাপত্র / TESTIMONIAL</b>", styles["DocHeader"]))

    # 3. Meta
    cert_no = testimonial_data.get("certificate_no", "TST-DRAFT")
    issue_date = str(testimonial_data.get("issue_date", ""))
    meta_table_data = [
        [
            Paragraph(f"<b>ক্রমিক নং:</b> {cert_no}", styles["Body"]),
            Paragraph(f"<b>তারিখ:</b> {issue_date}", styles["Body"]),
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # 4. Testimonial Body Paragraph
    exam_name = testimonial_data.get("exam_name", "বার্ষিক পরীক্ষা")
    passing_year = str(testimonial_data.get("passing_year", ""))
    gpa = str(testimonial_data.get("gpa", "5.00"))
    character = testimonial_data.get("character", "উত্তম")
    name_bn = student_data.get("name_bn", "")
    name_en = student_data.get("name_en", "")

    testimonial_text = (
        f"এই মর্মে প্রত্যয়ন করা যাচ্ছে যে, <b>{name_bn}</b> ({name_en}), "
        f"পরিচিতি নং <b>{student_data.get('student_id', '')}</b>, "
        f"শ্রেণি <b>{enrollment_data.get('class_name', '')}</b>, "
        f"শাখা <b>{enrollment_data.get('section_name', '')}</b>, "
        f"অত্র প্রতিষ্ঠানের একজন নিয়মিত ও নিষ্ঠাবান শিক্ষার্থী ছিল। সে <b>{passing_year}</b> সালের "
        f"<b>{exam_name}</b> পরীক্ষায় অংশগ্রহণ করিয়া জিপিএ (GPA) <b>{gpa}</b> (স্কেল ৫.০০) "
        f"অর্জন পূর্বক কৃতিত্বের সহিত উত্তীর্ণ হইয়াছে।<br/><br/>"
        f"অধ্যয়নকালে তাহার নৈতিক চরিত্র ও স্বভাব <b>{character}</b> ছিল। "
        f"আমার জানামতে সে প্রতিষ্ঠান বা সমাজ বিরোধী কোনো কর্মকাণ্ডে জড়িত ছিল না।<br/><br/>"
        f"আমরা তাহার উজ্জ্বল ভবিষ্যৎ, সুস্বাস্থ্য ও জীবনের সার্বিক উন্নতি কামনা করি।"
    )
    story.append(Paragraph(testimonial_text, styles["Body"]))
    story.append(Spacer(1, 80))

    # 5. Signatures
    sig_data = [
        [
            Paragraph("______________________<br/>যাচাইকারী", styles["Footer"]),
            Paragraph("______________________<br/><b>প্রধান শিক্ষক / অধ্যক্ষ</b>", styles["Footer"]),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(sig_table)

    return render_story_to_pdf(story, pagesize=A4, margin=36.0)


def generate_student_id_card_pdf(
    institution_data: dict[str, Any],
    student_data: dict[str, Any],
    enrollment_data: dict[str, Any],
    id_card_data: dict[str, Any],
) -> bytes:
    """Generate printable student ID badge PDF."""
    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    # Compact single-badge or multi-badge format
    inst_name_bn = institution_data.get("name_bn") or institution_data.get("name", "বিদ্যালয়")
    inst_name_en = institution_data.get("name_en") or institution_data.get("name", "School")

    story.append(Paragraph(f"<b>{inst_name_bn}</b>", styles["Title"]))
    story.append(Paragraph(f"{inst_name_en}", styles["Subtitle"]))
    story.append(Paragraph("<b>STUDENT IDENTITY CARD</b>", styles["DocHeader"]))

    card_items = [
        ("Student ID", student_data.get("student_id", "")),
        ("Name (EN)", student_data.get("name_en", "")),
        ("নাম (বাংলা)", student_data.get("name_bn", "")),
        ("Class", enrollment_data.get("class_name", "")),
        ("Section", enrollment_data.get("section_name", "")),
        ("Roll No", str(enrollment_data.get("roll_no", ""))),
        ("Blood Group", student_data.get("blood_group", "")),
        ("Emergency Contact", student_data.get("emergency_contact_phone", "N/A")),
        ("Card No", id_card_data.get("card_no", "")),
    ]

    card_table_data = [
        [Paragraph(f"<b>{k}</b>", styles["Label"]), Paragraph(f": {v}", styles["Value"])]
        for k, v in card_items
    ]
    card_table = Table(card_table_data, colWidths=[2.0 * inch, 4.0 * inch])
    card_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, HexColor("#1E3A8A")),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(card_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("স্বাক্ষর: ____________________ (প্রধান শিক্ষক)", styles["Footer"]))

    return render_story_to_pdf(story, pagesize=A4, margin=36.0)
