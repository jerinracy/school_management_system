"""Bilingual (Bangla & English) Progress Report Card generator."""

import io
import zipfile
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.files.base import ContentFile
from django.db.models import Max
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer, Table, TableStyle

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import User
from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.core.pdf.engine import get_bengali_stylesheet, render_story_to_pdf
from apps.exams.models import Exam
from apps.results.models import (
    ExamResult,
    ReportCard,
    ReportCardTemplateStyle,
    SubjectResult,
)


def _get_student_attendance_summary(
    student_id: UUID,
    start_date: Any,
    end_date: Any,
) -> dict[str, Any]:
    """Calculate term attendance metrics from DailyAttendance records."""
    if not start_date or not end_date:
        return {
            "working_days": 0,
            "present_days": 0,
            "absent_days": 0,
            "late_days": 0,
            "percentage": Decimal("0.00"),
        }

    records = DailyAttendance.objects.filter(
        student_id=student_id,
        date__gte=start_date,
        date__lte=end_date,
    )
    working_days = records.exclude(
        status__in=[AttendanceStatus.HOLIDAY, AttendanceStatus.WEEKEND]
    ).count()

    present_days = records.filter(status=AttendanceStatus.PRESENT).count()
    late_days = records.filter(status=AttendanceStatus.LATE).count()
    absent_days = records.filter(status=AttendanceStatus.ABSENT).count()

    att_count = present_days + late_days
    pct = Decimal("0.00")
    if working_days > 0:
        pct = Decimal(str((att_count / working_days) * 100)).quantize(Decimal("0.01"))

    return {
        "working_days": working_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "percentage": pct,
    }


def generate_student_report_card_pdf(exam_result_id: UUID | str) -> bytes:
    """Render a comprehensive bilingual Progress Report Card PDF using authentic Bangla typography."""
    exam_result = ExamResult.objects.select_related(
        "exam",
        "exam__session",
        "institution",
        "student",
        "enrollment",
        "enrollment__class_level",
        "enrollment__section",
        "enrollment__shift",
    ).get(id=exam_result_id)

    exam = exam_result.exam
    inst = exam_result.institution
    student = exam_result.student
    enr = exam_result.enrollment

    # Retrieve subject results and class-highest marks per subject
    subj_results = list(
        SubjectResult.objects.filter(
            exam=exam,
            student=student,
            is_deleted=False,
        )
        .select_related("exam_subject__subject")
        .order_by("exam_subject__subject__code", "exam_subject__subject__name_en")
    )

    highest_marks_query = (
        SubjectResult.objects.filter(
            exam=exam,
            exam_subject__class_level=enr.class_level,
            is_deleted=False,
        )
        .values("exam_subject_id")
        .annotate(max_mark=Max("total_marks"))
    )
    highest_marks = {item["exam_subject_id"]: item["max_mark"] for item in highest_marks_query}

    # Attendance statistics
    att = _get_student_attendance_summary(student.id, exam.start_date, exam.end_date)

    styles = get_bengali_stylesheet()
    font_name = styles["Title"].fontName
    story: list[Flowable] = []

    # 1. School Header
    inst_bn = inst.name_bn or inst.name_en
    inst_en = inst.name_en
    eiin_str = f"EIIN: {inst.eiin}" if inst.eiin else ""
    addr_str = inst.address_line or ""
    meta_line = f"{eiin_str} | {addr_str}".strip(" |")

    story.append(Paragraph(f"<b>{inst_bn}</b>", styles["Title"]))
    if inst_en != inst_bn:
        story.append(Paragraph(f"<b>{inst_en}</b>", styles["Subtitle"]))
    if meta_line:
        story.append(Paragraph(meta_line, styles["Footer"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1E3A8A"), spaceAfter=6))

    # 2. Document Title
    doc_title = "শিক্ষার্থীর অগ্রগতি প্রতিবেদন / PROGRESS REPORT CARD"
    story.append(Paragraph(f"<b>{doc_title}</b>", styles["DocHeader"]))
    exam_meta = f"পরীক্ষা: {exam.name} | শিক্ষাবর্ষ: {exam.session.name}"
    story.append(Paragraph(exam_meta, styles["Subtitle"]))
    story.append(Spacer(1, 4))

    # 3. Student Particulars Table
    sec_name = enr.section.name if enr.section else "N/A"
    shift_name = enr.shift.name if enr.shift else "Morning"
    stu_bn = student.name_bn or student.name_en
    bio_data = [
        [
            Paragraph(f"<b>শিক্ষার্থীর নাম:</b> {stu_bn}", styles["Body"]),
            Paragraph(f"<b>Student ID:</b> {student.student_id}", styles["Body"]),
        ],
        [
            Paragraph(f"<b>Name (English):</b> {student.name_en}", styles["Body"]),
            Paragraph(f"<b>রোল নম্বর (Roll):</b> {enr.roll_no}", styles["Body"]),
        ],
        [
            Paragraph(
                f"<b>শ্রেণী (Class):</b> {enr.class_level.name} | <b>শাখা (Section):</b> {sec_name}",
                styles["Body"],
            ),
            Paragraph(
                f"<b>শিফট (Shift):</b> {shift_name} | <b>উপস্থিতি:</b> {att['percentage']}%",
                styles["Body"],
            ),
        ],
    ]
    bio_table = Table(bio_data, colWidths=[290, 230])
    bio_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
            ]
        )
    )
    story.append(bio_table)
    story.append(Spacer(1, 8))

    # 4. Detailed Subject Marks Table
    marks_headers = [
        "বিষয় (Subject)",
        "পূর্ণমান\nFull",
        "CQ\nসৃজনশীল",
        "MCQ\nনৈর্বাচনী",
        "PR\nব্যবহারিক",
        "প্রাপ্ত\nTotal",
        "সর্বোচ্চ\nHighest",
        "GP",
        "Grade",
    ]
    marks_rows = [marks_headers]

    for sr in subj_results:
        s_name = sr.exam_subject.subject.name_bn or sr.exam_subject.subject.name_en
        if sr.is_fourth_subject:
            s_name += " (৪র্থ বিষয় / 4th)"

        cq = str(int(sr.creative_marks)) if sr.creative_marks is not None else "-"
        mcq = str(int(sr.mcq_marks)) if sr.mcq_marks is not None else "-"
        pr = str(int(sr.practical_marks)) if sr.practical_marks is not None else "-"
        tot = str(int(sr.total_marks))
        high_m = str(int(highest_marks.get(sr.exam_subject_id, sr.total_marks)))

        marks_rows.append(
            [
                s_name,
                str(int(sr.full_marks)),
                cq,
                mcq,
                pr,
                tot,
                high_m,
                str(sr.grade_point),
                sr.letter_grade,
            ]
        )

    marks_table = Table(marks_rows, colWidths=[160, 45, 45, 45, 45, 45, 45, 40, 50], repeatRows=1)
    marks_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(marks_table)
    story.append(Spacer(1, 8))

    # 5. Grand Summary Block & Bangladesh Grading Scale Legend
    res_badge = "উত্তীর্ণ (PASSED)" if exam_result.is_passed else "অনুত্তীর্ণ (FAILED)"
    summary_data = [
        [
            Paragraph("<b>সর্বমোট প্রাপ্ত নম্বর (Total Marks):</b>", styles["Body"]),
            Paragraph(
                f"{exam_result.total_marks} / {exam_result.total_full_marks} ({exam_result.percentage}%)",
                styles["Body"],
            ),
            Paragraph("<b>চূড়ান্ত জিপিএ (Final GPA):</b>", styles["Body"]),
            Paragraph(
                f"<b>{exam_result.final_gpa} (Grade: {exam_result.final_grade})</b>", styles["Body"]
            ),
        ],
        [
            Paragraph("<b>নৈর্বাচনিক ব্যতীত জিপিএ:</b>", styles["Body"]),
            Paragraph(f"{exam_result.gpa_without_fourth}", styles["Body"]),
            Paragraph("<b>৪র্থ বিষয়ের বোনাস পয়েন্ট:</b>", styles["Body"]),
            Paragraph(f"+{exam_result.fourth_subject_bonus}", styles["Body"]),
        ],
        [
            Paragraph("<b>মেধা স্থান (শাখা / Section Rank):</b>", styles["Body"]),
            Paragraph(f"{exam_result.section_position or 'N/A'}", styles["Body"]),
            Paragraph("<b>মেধা স্থান (শ্রেণী / Class Rank):</b>", styles["Body"]),
            Paragraph(f"{exam_result.class_position or 'N/A'}", styles["Body"]),
        ],
        [
            Paragraph("<b>ফলাফলের অবস্থা (Result Status):</b>", styles["Body"]),
            Paragraph(f"<b>{res_badge}</b>", styles["Body"]),
            Paragraph("<b>ব্যর্থ বিষয় (Failed Subjects):</b>", styles["Body"]),
            Paragraph(
                f"{', '.join(exam_result.failed_subjects_summary) if exam_result.failed_subjects_summary else 'নেই (None)'}",
                styles["Body"],
            ),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[150, 110, 150, 110])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#94A3B8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # 6. NCTB Grading Scale Legend
    legend_data = [
        ["নম্বর ব্যাপ্তি (Marks)", "80-100", "70-79", "60-69", "50-59", "40-49", "33-39", "0-32"],
        ["গ্রেড (Grade)", "A+", "A", "A-", "B", "C", "D", "F"],
        ["গ্রেড পয়েন্ট (GP)", "5.00", "4.00", "3.50", "3.00", "2.00", "1.00", "0.00"],
    ]
    legend_table = Table(legend_data, colWidths=[110, 58, 58, 58, 58, 58, 58, 58])
    legend_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(legend_table)
    story.append(Spacer(1, 24))

    # 7. Signature Blocks
    sig_data = [
        [
            "....................................\nশ্রেণী শিক্ষকের স্বাক্ষর\n(Class Teacher)",
            "....................................\nঅভিভাবকের স্বাক্ষর\n(Guardian)",
            "....................................\nপ্রধান শিক্ষক / অধ্যক্ষের স্বাক্ষর\n(Head Teacher / Principal)",
        ]
    ]
    sig_table = Table(sig_data, colWidths=[170, 170, 180])
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#334155")),
            ]
        )
    )
    story.append(sig_table)

    return render_story_to_pdf(story, pagesize=A4, margin=24)


def create_or_update_report_card(
    exam_result_id: UUID | str,
    template_style: str = ReportCardTemplateStyle.DEFAULT_BD,
    user: User | None = None,
) -> ReportCard:
    """Generate the official progress report card PDF and save it to the ReportCard model."""
    exam_result = ExamResult.objects.select_related("exam", "student", "enrollment").get(
        id=exam_result_id
    )

    pdf_bytes = generate_student_report_card_pdf(exam_result.id)
    filename = f"report_card_{exam_result.exam.id}_{exam_result.student.student_id}.pdf"

    report_card, _ = ReportCard.objects.update_or_create(
        institution=exam_result.institution,
        exam=exam_result.exam,
        student=exam_result.student,
        defaults={
            "enrollment": exam_result.enrollment,
            "exam_result": exam_result,
            "template_style": template_style,
            "generated_by": user,
        },
    )
    report_card.file.save(filename, ContentFile(pdf_bytes), save=True)
    return report_card


def generate_bulk_report_cards_zip(
    exam_id: UUID | str,
    class_level_id: UUID | str,
    section_id: UUID | str | None = None,
    user: User | None = None,
) -> bytes:
    """Batch-generate report cards for all students in a class/section and pack into a ZIP archive."""
    exam = Exam.objects.get(id=exam_id)
    class_level = ClassLevel.objects.get(id=class_level_id)
    section = Section.objects.get(id=section_id) if section_id else None

    res_qs = ExamResult.objects.filter(
        exam=exam,
        enrollment__class_level=class_level,
        is_deleted=False,
    ).select_related("student", "enrollment")
    if section:
        res_qs = res_qs.filter(enrollment__section=section)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for er in res_qs:
            card = create_or_update_report_card(er.id, user=user)
            if card.file:
                with card.file.open("rb") as f:
                    pdf_data = f.read()
                roll = er.enrollment.roll_no or 0
                f_name = f"Roll_{roll:02d}_{er.student.student_id}.pdf"
                zf.writestr(f_name, pdf_data)

    return zip_buffer.getvalue()
