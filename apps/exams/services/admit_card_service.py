"""Admit card PDF generator with authentic Bengali typography."""

from uuid import UUID

from reportlab.lib.colors import HexColor
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.core.pdf.engine import get_bengali_stylesheet, render_story_to_pdf
from apps.exams.models import AdmitCard, ExamRoutine
from apps.students.models import EnrollmentStatus, StudentEnrollment


def generate_admit_card_pdf(admit_card_id: UUID | str) -> bytes:
    """Generate printable official Admit Card (প্রবেশপত্র) PDF for a student.

    Returns:
        bytes of generated PDF document.
    """
    card = AdmitCard.objects.select_related("exam", "student", "institution", "exam__session").get(
        id=admit_card_id
    )
    exam = card.exam
    student = card.student
    institution = card.institution

    # Find active student enrollment for this exam's session
    enrollment = (
        StudentEnrollment.objects.filter(
            student=student,
            session=exam.session,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("class_level", "section")
        .first()
    )

    class_name = enrollment.class_level.name if enrollment else "N/A"
    section_name = enrollment.section.name if enrollment and enrollment.section else "N/A"
    roll_no = str(enrollment.roll_no) if enrollment else "N/A"

    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    # 1. Institution Header
    inst_name_bn = institution.name_bn or institution.name_en
    inst_name_en = institution.name_en
    eiin = institution.eiin or ""
    address = institution.address or ""

    story.append(Paragraph(f"<b>{inst_name_bn}</b>", styles["Title"]))
    if inst_name_en != inst_name_bn:
        story.append(Paragraph(f"{inst_name_en}", styles["Subtitle"]))
    meta_line = f"EIIN: {eiin} | {address}" if eiin else address
    if meta_line:
        story.append(Paragraph(meta_line, styles["Footer"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1E3A8A"), spaceAfter=10))

    # 2. Document Title & Exam Name
    story.append(Paragraph("<b>প্রবেশপত্র / ADMIT CARD</b>", styles["DocHeader"]))
    story.append(Paragraph(f"<b>{exam.name}</b>", styles["Subtitle"]))
    story.append(Spacer(1, 10))

    # 3. Student Particulars Table
    student_table_data = [
        [
            Paragraph(
                f"<b>শিক্ষার্থীর নাম / Name:</b> {student.name_en} ({student.name_bn})",
                styles["Body"],
            ),
            Paragraph(f"<b>কার্ড নং / Card No:</b> {card.card_number}", styles["Body"]),
        ],
        [
            Paragraph(f"<b>শিক্ষার্থী আইডি / Student ID:</b> {student.student_id}", styles["Body"]),
            Paragraph(f"<b>রোল নং / Roll No:</b> {roll_no}", styles["Body"]),
        ],
        [
            Paragraph(f"<b>শ্রেণি / Class:</b> {class_name}", styles["Body"]),
            Paragraph(f"<b>শাখা / Section:</b> {section_name}", styles["Body"]),
        ],
    ]
    student_table = Table(student_table_data, colWidths=["60%", "40%"])
    student_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(student_table)
    story.append(Spacer(1, 12))

    # 4. Exam Routine Table for student's class level
    routine_qs = (
        ExamRoutine.objects.filter(
            exam=exam,
        )
        .select_related("exam_subject__subject", "exam_subject__class_level")
        .order_by("exam_date", "start_time")
    )

    if enrollment:
        routine_qs = routine_qs.filter(exam_subject__class_level=enrollment.class_level)

    routine_rows = [
        [
            Paragraph("<b>তারিখ / Date</b>", styles["Body"]),
            Paragraph("<b>সময় / Time</b>", styles["Body"]),
            Paragraph("<b>বিষয় / Subject</b>", styles["Body"]),
            Paragraph("<b>কক্ষ / Room</b>", styles["Body"]),
        ]
    ]

    for item in routine_qs:
        time_str = f"{item.start_time.strftime('%I:%M %p')} - {item.end_time.strftime('%I:%M %p')}"
        subj_name = f"{item.exam_subject.subject.name_en} ({item.exam_subject.subject.code})"
        routine_rows.append(
            [
                Paragraph(str(item.exam_date), styles["Body"]),
                Paragraph(time_str, styles["Body"]),
                Paragraph(subj_name, styles["Body"]),
                Paragraph(item.room_number or "-", styles["Body"]),
            ]
        )

    if len(routine_rows) > 1:
        routine_table = Table(routine_rows, colWidths=["20%", "30%", "35%", "15%"])
        routine_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(Paragraph("<b>পরীক্ষার সময়সূচী / Exam Schedule:</b>", styles["Body"]))
        story.append(Spacer(1, 4))
        story.append(routine_table)
    story.append(Spacer(1, 20))

    # 5. Instructions & Signature Block
    instructions = (
        "<b>নির্দেশাবলী / Instructions:</b><br/>"
        "১. পরীক্ষা শুরুর কমপক্ষে ১৫ মিনিট পূর্বে পরীক্ষার হলে উপস্থিত হতে হবে।<br/>"
        "২. প্রবেশপত্র ব্যতিরেকে কোনো শিক্ষার্থীকে পরীক্ষায় অংশগ্রহণ করতে দেওয়া হবে না।<br/>"
        "৩. পরীক্ষার হলে মোবাইল ফোন বা কোনো প্রকার ইলেকট্রনিক ডিভাইস আনা সম্পূর্ণ নিষিদ্ধ।"
    )
    story.append(Paragraph(instructions, styles["Footer"]))
    story.append(Spacer(1, 25))

    sig_data = [
        [
            Paragraph("শিক্ষার্থীর স্বাক্ষর<br/>Candidate's Signature", styles["Footer"]),
            Paragraph("পরীক্ষা নিয়ন্ত্রক / শাখা প্রধান<br/>Exam Controller", styles["Footer"]),
            Paragraph("অধ্যক্ষ / প্রধান শিক্ষক<br/>Principal / Headmaster", styles["Footer"]),
        ]
    ]
    sig_table = Table(sig_data, colWidths=["33%", "33%", "34%"])
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LINEABOVE", (0, 0), (-1, -1), 0.5, HexColor("#64748B")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(sig_table)

    return render_story_to_pdf(story)
