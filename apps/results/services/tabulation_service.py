"""Tabulation Broadsheet generation service (Excel and PDF formats)."""

import io
from typing import Any
from uuid import UUID

import openpyxl
from django.core.files.base import ContentFile
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import User
from apps.core.pdf.engine import get_bengali_stylesheet, render_story_to_pdf
from apps.exams.models import Exam, ExamSubject
from apps.results.models import (
    ExamResult,
    SubjectResult,
    TabulationSheet,
    TabulationSheetFormat,
)


def _get_tabulation_data(
    exam_id: UUID | str,
    class_level_id: UUID | str,
    section_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Retrieve all structured marks, subjects, and student results needed for tabulation."""
    exam = Exam.objects.select_related("institution", "session").get(id=exam_id)
    class_level = ClassLevel.objects.get(id=class_level_id)
    section = Section.objects.get(id=section_id) if section_id else None

    # Retrieve all exam subjects for this exam & class level
    exam_subjects = list(
        ExamSubject.objects.filter(exam=exam, class_level=class_level)
        .select_related("subject")
        .order_by("subject__code", "subject__name_en")
    )

    # Retrieve exam results for students in this class/section
    res_qs = (
        ExamResult.objects.filter(
            exam=exam,
            enrollment__class_level=class_level,
            is_deleted=False,
        )
        .select_related("student", "enrollment", "enrollment__section")
        .order_by("enrollment__section__name", "enrollment__roll_no")
    )
    if section:
        res_qs = res_qs.filter(enrollment__section=section)

    exam_results = list(res_qs)
    student_ids = [r.student_id for r in exam_results]

    # Retrieve subject results mapped by (student_id, exam_subject_id)
    subj_results = list(
        SubjectResult.objects.filter(
            exam=exam,
            student_id__in=student_ids,
            is_deleted=False,
        ).select_related("exam_subject")
    )
    subj_marks_map: dict[tuple[UUID, UUID], SubjectResult] = {
        (sr.student_id, sr.exam_subject_id): sr for sr in subj_results
    }

    return {
        "exam": exam,
        "class_level": class_level,
        "section": section,
        "institution": exam.institution,
        "exam_subjects": exam_subjects,
        "exam_results": exam_results,
        "subj_marks_map": subj_marks_map,
    }


def _write_tabulation_excel_headers(
    ws: Any,
    inst: Any,
    exam: Exam,
    class_level: ClassLevel,
    section: Section | None,
    exam_subjects: list[ExamSubject],
) -> None:
    """Build the title and two-tier header rows in the Excel worksheet."""
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    sub_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    summary_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

    font_title = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    font_sub = Font(name="Calibri", size=11, bold=True, color="475569")
    font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 1. Sheet Title block
    ws.merge_cells("A1:N1")
    ws["A1"] = inst.name_en or inst.name_bn
    ws["A1"].font = font_title
    ws["A1"].alignment = align_center

    sec_name = f" - Section: {section.name}" if section else " - All Sections"
    ws.merge_cells("A2:N2")
    ws["A2"] = (
        f"Tabulation Sheet | Exam: {exam.name} ({exam.session.name}) | Class: {class_level.name}{sec_name}"
    )
    ws["A2"].font = font_sub
    ws["A2"].alignment = align_center

    # 2. Fixed left headers
    for col, val in [(1, "Roll"), (2, "Student ID"), (3, "Student Name")]:
        ws.merge_cells(start_row=4, start_column=col, end_row=5, end_column=col)
        c = ws.cell(row=4, column=col, value=val)
        c.font = font_hdr
        c.fill = header_fill
        c.alignment = align_center

    col_idx = 4
    # Subject Headers: CQ, MCQ, Prac, Total, GP, Grade
    for es in exam_subjects:
        ws.merge_cells(start_row=4, start_column=col_idx, end_row=4, end_column=col_idx + 5)
        hdr_cell = ws.cell(row=4, column=col_idx, value=es.subject.name_en)
        hdr_cell.font = font_hdr
        hdr_cell.fill = sub_fill
        hdr_cell.alignment = align_center

        for i, sub_name in enumerate(["CQ", "MCQ", "PR", "Tot", "GP", "Gr"]):
            c = ws.cell(row=5, column=col_idx + i, value=sub_name)
            c.font = font_hdr
            c.fill = sub_fill
            c.alignment = align_center
            c.border = thin_border
        col_idx += 6

    # Summary Headers
    summary_headers = [
        "Grand Total",
        "GPA w/o 4th",
        "4th Bonus",
        "Final GPA",
        "Grade",
        "Sec Pos",
        "Class Pos",
        "Result",
        "Failed Subjects",
    ]
    for s_hdr in summary_headers:
        ws.merge_cells(start_row=4, start_column=col_idx, end_row=5, end_column=col_idx)
        c = ws.cell(row=4, column=col_idx, value=s_hdr)
        c.font = font_hdr
        c.fill = summary_fill
        c.alignment = align_center
        c.border = thin_border
        col_idx += 1


def _write_tabulation_excel_student_row(
    ws: Any,
    row_idx: int,
    er: ExamResult,
    exam_subjects: list[ExamSubject],
    subj_marks_map: dict[tuple[UUID, UUID], SubjectResult],
    row_fill: Any,
) -> None:
    """Populate a single student's row across subjects and summary metrics."""
    font_data = Font(name="Calibri", size=10, bold=False, color="000000")
    font_bold = Font(name="Calibri", size=10, bold=True, color="000000")
    font_fail = Font(name="Calibri", size=10, bold=True, color="DC2626")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    # Roll, ID, Name
    ws.cell(row=row_idx, column=1, value=er.enrollment.roll_no).font = font_bold
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=2, value=er.student.student_id).font = font_data
    ws.cell(row=row_idx, column=2).alignment = align_center
    ws.cell(row=row_idx, column=3, value=er.student.name_en).font = font_bold
    ws.cell(row=row_idx, column=3).alignment = align_left

    c_col = 4
    for es in exam_subjects:
        sr = subj_marks_map.get((er.student_id, es.id))
        cq_v: float | str
        mcq_v: float | str
        pr_v: float | str
        tot_v: float | str
        gp_v: float | str
        gr_v: str
        is_pass: bool
        if sr:
            cq_v = float(sr.creative_marks) if sr.creative_marks is not None else "-"
            mcq_v = float(sr.mcq_marks) if sr.mcq_marks is not None else "-"
            pr_v = float(sr.practical_marks) if sr.practical_marks is not None else "-"
            tot_v = float(sr.total_marks)
            gp_v = float(sr.grade_point)
            gr_v = sr.letter_grade
            is_pass = sr.is_passed
        else:
            cq_v, mcq_v, pr_v, tot_v, gp_v, gr_v, is_pass = "-", "-", "-", "-", "-", "-", True

        for i, val in enumerate([cq_v, mcq_v, pr_v, tot_v, gp_v, gr_v]):
            cell = ws.cell(row=row_idx, column=c_col + i, value=val)
            cell.font = font_data if is_pass else font_fail
            cell.alignment = align_center
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill
        c_col += 6

    # Summary metrics
    sum_vals: list[Any] = [
        float(er.total_marks),
        float(er.gpa_without_fourth),
        float(er.fourth_subject_bonus),
        float(er.final_gpa),
        er.final_grade,
        er.section_position or "-",
        er.class_position or "-",
        "PASSED" if er.is_passed else "FAILED",
        ", ".join(er.failed_subjects_summary) if er.failed_subjects_summary else "-",
    ]
    for i, val in enumerate(sum_vals):
        cell = ws.cell(row=row_idx, column=c_col + i, value=val)
        if i in [3, 4, 7] and not er.is_passed:
            cell.font = font_fail
        else:
            cell.font = font_bold if i in [0, 3, 4, 7] else font_data
        cell.alignment = align_center
        cell.border = thin_border
        if row_fill:
            cell.fill = row_fill

    for c_idx in range(1, 4):
        ws.cell(row=row_idx, column=c_idx).border = thin_border
        if row_fill:
            ws.cell(row=row_idx, column=c_idx).fill = row_fill


def generate_tabulation_excel(
    exam_id: UUID | str,
    class_level_id: UUID | str,
    section_id: UUID | str | None = None,
) -> bytes:
    """Generate Excel (.xlsx) Broadsheet Tabulation with per-subject component breakdown."""
    data = _get_tabulation_data(exam_id, class_level_id, section_id)
    exam = data["exam"]
    class_level = data["class_level"]
    section = data["section"]
    inst = data["institution"]
    exam_subjects: list[ExamSubject] = data["exam_subjects"]
    exam_results: list[ExamResult] = data["exam_results"]
    subj_marks_map: dict[tuple[UUID, UUID], SubjectResult] = data["subj_marks_map"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tabulation Sheet"
    ws.views.sheetView[0].showGridLines = True

    _write_tabulation_excel_headers(ws, inst, exam, class_level, section, exam_subjects)

    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    current_row = 6
    for idx, er in enumerate(exam_results):
        row_fill = zebra_fill if idx % 2 == 1 else None
        _write_tabulation_excel_student_row(
            ws, current_row, er, exam_subjects, subj_marks_map, row_fill
        )
        current_row += 1

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 24

    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()


def generate_tabulation_pdf(
    exam_id: UUID | str,
    class_level_id: UUID | str,
    section_id: UUID | str | None = None,
) -> bytes:
    """Generate printable PDF Broadsheet Tabulation in Landscape orientation."""
    data = _get_tabulation_data(exam_id, class_level_id, section_id)
    exam = data["exam"]
    class_level = data["class_level"]
    section = data["section"]
    inst = data["institution"]
    exam_subjects: list[ExamSubject] = data["exam_subjects"]
    exam_results: list[ExamResult] = data["exam_results"]
    subj_marks_map: dict[tuple[UUID, UUID], SubjectResult] = data["subj_marks_map"]

    styles = get_bengali_stylesheet()
    story: list[Flowable] = []

    # Title & Header
    inst_name = inst.name_en or inst.name_bn
    story.append(Paragraph(f"<b>{inst_name}</b>", styles["Title"]))
    sec_name = f" - Section: {section.name}" if section else " - All Sections"
    meta = f"Examination: {exam.name} ({exam.session.name}) | Class: {class_level.name}{sec_name}"
    story.append(Paragraph(f"<b>TABULATION SHEET</b> — {meta}", styles["Subtitle"]))
    story.append(Spacer(1, 6))

    # Construct tabular data: Roll | ID | Name | Subj1 Tot (GP) | Subj2... | Total | GPA | Grade | Rank | Status
    table_headers = ["Roll", "ID", "Name"]
    for es in exam_subjects:
        short_name = es.subject.name_en[:8]
        table_headers.append(f"{short_name}\n(Tot/GP)")
    table_headers.extend(["Total", "GPA", "Grade", "Rank", "Status"])

    table_data = [table_headers]

    for er in exam_results:
        row = [
            str(er.enrollment.roll_no),
            er.student.student_id,
            er.student.name_en[:18],
        ]
        for es in exam_subjects:
            sr = subj_marks_map.get((er.student_id, es.id))
            if sr:
                row.append(f"{int(sr.total_marks)}\n({sr.grade_point})")
            else:
                row.append("-")

        rank_val = f"S:{er.section_position}/C:{er.class_position}" if er.section_position else "-"
        row.extend(
            [
                str(int(er.total_marks)),
                str(er.final_gpa),
                er.final_grade,
                rank_val,
                "PASS" if er.is_passed else "FAIL",
            ]
        )
        table_data.append(row)

    col_widths = [28, 50, 80] + [40] * len(exam_subjects) + [40, 32, 32, 45, 38]
    pdf_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    pdf_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                ("FONTNAME", (0, 0), (-1, 0), styles["Title"].fontName),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "LEFT"),  # Student name left-aligned
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(pdf_table)
    story.append(Spacer(1, 20))

    # Committee Signatures block
    sig_data = [
        ["Prepared By", "Checked By", "Class Teacher", "Head Teacher / Principal"],
        [
            "...................",
            "...................",
            "...................",
            "...................",
        ],
    ]
    sig_table = Table(sig_data, colWidths=[180, 180, 180, 180])
    sig_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), styles["Title"].fontName),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#334155")),
            ]
        )
    )
    story.append(sig_table)

    return render_story_to_pdf(story, pagesize=landscape(A4), margin=18)


def create_tabulation_sheet_record(
    exam_id: UUID | str,
    class_level_id: UUID | str,
    section_id: UUID | str | None = None,
    file_format: str = TabulationSheetFormat.EXCEL,
    user: User | None = None,
) -> TabulationSheet:
    """Generate the file and persist an official TabulationSheet record."""
    if str(file_format).lower() in ["excel", "xlsx", "csv"]:
        file_format = TabulationSheetFormat.EXCEL
    else:
        file_format = TabulationSheetFormat.PDF

    exam = Exam.objects.select_related("institution").get(id=exam_id)
    class_level = ClassLevel.objects.get(id=class_level_id)
    section = Section.objects.get(id=section_id) if section_id else None

    # Compute latest version number
    prev = (
        TabulationSheet.objects.filter(
            institution=exam.institution,
            exam=exam,
            class_level=class_level,
            section=section,
            file_format=file_format,
            is_deleted=False,
        )
        .order_by("-version")
        .first()
    )
    version = (prev.version + 1) if prev else 1

    if file_format == TabulationSheetFormat.EXCEL:
        content = generate_tabulation_excel(exam_id, class_level_id, section_id)
        ext = "xlsx"
    else:
        content = generate_tabulation_pdf(exam_id, class_level_id, section_id)
        ext = "pdf"

    sec_tag = f"_sec_{section.name}" if section else ""
    filename = f"tabulation_{exam.id}_{class_level.id}{sec_tag}_v{version}.{ext}"

    total_count = ExamResult.objects.filter(
        exam=exam,
        enrollment__class_level=class_level,
        is_deleted=False,
    )
    if section:
        total_count = total_count.filter(enrollment__section=section)

    record = TabulationSheet.objects.create(
        institution=exam.institution,
        exam=exam,
        class_level=class_level,
        section=section,
        file_format=file_format,
        version=version,
        generated_by=user,
        total_students=total_count.count(),
    )
    record.file.save(filename, ContentFile(content), save=True)
    return record
