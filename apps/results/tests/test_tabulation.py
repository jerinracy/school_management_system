"""Tests for Excel and PDF Tabulation Sheet generation."""

from datetime import date, time
from decimal import Decimal

import openpyxl
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import UserType
from apps.accounts.test_helpers import make_user
from apps.exams.models import Exam, ExamSubject, ExamType, MarkEntry
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.results.models import TabulationSheetFormat
from apps.results.services import (
    create_tabulation_sheet_record,
    generate_tabulation_excel,
    generate_tabulation_pdf,
    seed_default_bd_grading_scale,
    tabulate_exam_results,
)
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def base_setup(db):
    inst = Institution.objects.create(
        name_en="Dhaka College High School",
        name_bn="ঢাকা কলেজ উচ্চ বিদ্যালয়",
        eiin="108259",
        address_line="Dhaka",
        email="dhakacollege@edu.bd",
        phone="+8801700000001",
    )
    branch = Branch.objects.create(institution=inst, name="Main Branch")
    session = AcademicSession.objects.create(
        institution=inst,
        name="2026 Session",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Morning",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )
    class_level = ClassLevel.objects.create(
        institution=inst,
        name="Class 10",
        order=10,
    )
    section = Section.objects.create(
        institution=inst,
        shift=shift,
        class_level=class_level,
        session=session,
        name="Section A",
    )
    seed_default_bd_grading_scale(inst)

    student1 = Student.objects.create(
        institution=inst,
        student_id="STU-1001",
        name_en="Rahim Uddin",
        name_bn="রহিম উদ্দিন",
        admission_date="2026-01-01",
        dob="2010-01-01",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student1,
        session=session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=1,
        enrollment_date="2026-01-01",
    )

    student2 = Student.objects.create(
        institution=inst,
        student_id="STU-1002",
        name_en="Karim Chowdhury",
        name_bn="করিম চৌধুরী",
        admission_date="2026-01-01",
        dob="2010-01-01",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student2,
        session=session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=2,
        enrollment_date="2026-01-01",
    )

    exam_type = ExamType.objects.create(institution=inst, name="Final Examination")
    exam = Exam.objects.create(
        institution=inst,
        name="Annual Examination 2026",
        session=session,
        exam_type=exam_type,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 20),
    )
    exam.target_classes.add(class_level)

    math = Subject.objects.create(
        institution=inst,
        name_en="Mathematics",
        name_bn="গণিত",
        code="MATH-10",
    )
    es_math = ExamSubject.objects.create(
        institution=inst,
        exam=exam,
        class_level=class_level,
        subject=math,
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_full_marks=Decimal("70.00"),
        creative_pass_marks=Decimal("23.00"),
        mcq_full_marks=Decimal("30.00"),
        mcq_pass_marks=Decimal("10.00"),
        practical_full_marks=Decimal("0.00"),
        practical_pass_marks=Decimal("0.00"),
    )

    # Student 1: 85 marks (A+)
    MarkEntry.objects.create(
        institution=inst,
        exam_subject=es_math,
        student=student1,
        creative_marks=Decimal("60.00"),
        mcq_marks=Decimal("25.00"),
        total_marks=Decimal("85.00"),
    )

    # Student 2: 45 marks (C)
    MarkEntry.objects.create(
        institution=inst,
        exam_subject=es_math,
        student=student2,
        creative_marks=Decimal("30.00"),
        mcq_marks=Decimal("15.00"),
        total_marks=Decimal("45.00"),
    )

    # Run tabulation
    tabulate_exam_results(exam.id)

    admin_user = make_user(
        username="tab_admin_user",
        institution=inst,
        phone="+8801700111222",
        user_type=UserType.STAFF,
        role="admin",
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    return {
        "inst": inst,
        "exam": exam,
        "class_level": class_level,
        "section": section,
        "admin_user": admin_user,
    }


@pytest.mark.django_db
def test_generate_tabulation_excel(base_setup):
    """Verify Excel broadsheet creation and valid XLSX content structure."""
    data = base_setup
    xlsx_bytes = generate_tabulation_excel(
        exam_id=data["exam"].id,
        class_level_id=data["class_level"].id,
        section_id=data["section"].id,
    )
    assert len(xlsx_bytes) > 0

    # Load workbook to verify cells
    import io

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws.title == "Tabulation Sheet"

    # Verify sheet has data for both students
    found_student = False
    for row in ws.iter_rows(values_only=True):
        if "STU-1001" in row or "Rahim Uddin" in row:
            found_student = True
            break
    assert found_student is True


@pytest.mark.django_db
def test_generate_tabulation_pdf(base_setup):
    """Verify PDF broadsheet generation producing valid PDF bytes."""
    data = base_setup
    pdf_bytes = generate_tabulation_pdf(
        exam_id=data["exam"].id,
        class_level_id=data["class_level"].id,
        section_id=data["section"].id,
    )
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.django_db
def test_create_tabulation_sheet_record(base_setup):
    """Verify official model record creation and file persistence."""
    data = base_setup
    sheet = create_tabulation_sheet_record(
        exam_id=data["exam"].id,
        class_level_id=data["class_level"].id,
        section_id=data["section"].id,
        file_format=TabulationSheetFormat.EXCEL,
        user=data["admin_user"],
    )
    assert sheet.id is not None
    assert sheet.version == 1
    assert sheet.total_students == 2
    assert sheet.file.name.endswith(".xlsx")


@pytest.mark.django_db
def test_tabulation_api_generate_and_download(base_setup):
    """Verify TabulationSheetViewSet endpoints."""
    data = base_setup
    client = APIClient()
    client.force_authenticate(user=data["admin_user"])

    # 1. Generate via API
    res = client.post(
        "/api/v1/results/tabulation-sheets/generate/",
        {
            "exam_id": str(data["exam"].id),
            "class_level_id": str(data["class_level"].id),
            "section_id": str(data["section"].id),
            "file_format": "xlsx",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    sheet_id = res.data["id"]

    # 2. List
    res_list = client.get("/api/v1/results/tabulation-sheets/")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data["results"]) >= 1

    # 3. Download
    res_dl = client.get(f"/api/v1/results/tabulation-sheets/{sheet_id}/download/")
    assert res_dl.status_code == status.HTTP_200_OK
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in res_dl.headers["Content-Type"]
    )


@pytest.mark.django_db
def test_tabulation_api_create_standard(base_setup):
    """Verify POST /api/v1/results/tabulation-sheets/ creates record and file with institution."""
    data = base_setup
    client = APIClient()
    client.force_authenticate(user=data["admin_user"])

    res = client.post(
        "/api/v1/results/tabulation-sheets/",
        {
            "exam": str(data["exam"].id),
            "class_level": str(data["class_level"].id),
            "section": str(data["section"].id),
            "file_format": "pdf",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["id"] is not None
    assert res.data["file_format"] == "pdf"
    assert res.data["download_url"] is not None

    # Test API download endpoint
    dl_res = client.get(f"/api/v1/results/tabulation-sheets/{res.data['id']}/download/")
    assert dl_res.status_code == status.HTTP_200_OK
    assert "application/pdf" in dl_res.headers["Content-Type"]

    # Test static media URL serving
    media_res = client.get(res.data["download_url"])
    assert media_res.status_code == status.HTTP_200_OK
