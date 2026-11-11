"""Tests for Progress Report Card PDF and bulk ZIP generation."""

import zipfile
from datetime import date, time
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import UserType
from apps.accounts.test_helpers import make_user
from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.exams.models import Exam, ExamSubject, ExamType, MarkEntry
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.results.models import ExamResult
from apps.results.services import (
    create_or_update_report_card,
    generate_bulk_report_cards_zip,
    generate_student_report_card_pdf,
    seed_default_bd_grading_scale,
    tabulate_exam_results,
)
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def report_card_setup(db):
    inst = Institution.objects.create(
        name_en="Motijheel Govt Boys High School",
        name_bn="মতিঝিল সরকারি বালক উচ্চ বিদ্যালয়",
        eiin="108260",
        address_line="Motijheel, Dhaka",
        email="motijheel@edu.bd",
        phone="+8801700000002",
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
        name="Day Shift",
        start_time=time(11, 0),
        end_time=time(16, 0),
    )
    class_level = ClassLevel.objects.create(
        institution=inst,
        name="Class 9",
        order=9,
    )
    section = Section.objects.create(
        institution=inst,
        shift=shift,
        class_level=class_level,
        session=session,
        name="Padma",
    )
    seed_default_bd_grading_scale(inst)

    student = Student.objects.create(
        institution=inst,
        student_id="STU-9001",
        name_en="Tanvir Ahmed",
        name_bn="তানভীর আহমেদ",
        admission_date="2026-01-01",
        dob="2010-01-01",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=1,
        enrollment_date="2026-01-01",
    )

    # Add DailyAttendance records for term window
    DailyAttendance.objects.create(
        institution=inst,
        user_type="student",
        student=student,
        date=date(2026, 11, 2),
        status=AttendanceStatus.PRESENT,
    )
    DailyAttendance.objects.create(
        institution=inst,
        user_type="student",
        student=student,
        date=date(2026, 11, 3),
        status=AttendanceStatus.LATE,
    )
    DailyAttendance.objects.create(
        institution=inst,
        user_type="student",
        student=student,
        date=date(2026, 11, 4),
        status=AttendanceStatus.ABSENT,
    )

    exam_type = ExamType.objects.create(institution=inst, name="Half-Yearly")
    exam = Exam.objects.create(
        institution=inst,
        name="Half-Yearly Examination 2026",
        session=session,
        exam_type=exam_type,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 15),
    )
    exam.target_classes.add(class_level)

    subject = Subject.objects.create(
        institution=inst,
        name_en="English",
        name_bn="ইংরেজি",
        code="ENG-09",
    )
    es = ExamSubject.objects.create(
        institution=inst,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_full_marks=Decimal("100.00"),
        creative_pass_marks=Decimal("33.00"),
        mcq_full_marks=Decimal("0.00"),
        mcq_pass_marks=Decimal("0.00"),
        practical_full_marks=Decimal("0.00"),
        practical_pass_marks=Decimal("0.00"),
    )

    MarkEntry.objects.create(
        institution=inst,
        exam_subject=es,
        student=student,
        creative_marks=Decimal("78.00"),
        total_marks=Decimal("78.00"),
    )

    tabulate_exam_results(exam.id)
    exam_res = ExamResult.objects.get(exam=exam, student=student)

    admin_user = make_user(
        username="rc_admin_user",
        institution=inst,
        phone="+8801700111223",
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
        "student": student,
        "exam_res": exam_res,
        "admin_user": admin_user,
    }


@pytest.mark.django_db
def test_generate_student_report_card_pdf(report_card_setup):
    """Verify authentic bilingual ReportLab PDF generation for a single student."""
    data = report_card_setup
    pdf_bytes = generate_student_report_card_pdf(data["exam_res"].id)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.django_db
def test_create_or_update_report_card_record(report_card_setup):
    """Verify ReportCard model instance persistence."""
    data = report_card_setup
    card = create_or_update_report_card(
        exam_result_id=data["exam_res"].id,
        user=data["admin_user"],
    )
    assert card.id is not None
    assert card.file.name.endswith(".pdf")
    assert card.student_id == data["student"].id


@pytest.mark.django_db
def test_generate_bulk_report_cards_zip(report_card_setup):
    """Verify batch report card generation and valid ZIP container creation."""
    import io

    data = report_card_setup
    zip_bytes = generate_bulk_report_cards_zip(
        exam_id=data["exam"].id,
        class_level_id=data["class_level"].id,
        section_id=data["section"].id,
    )
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        file_list = zf.namelist()
        assert len(file_list) == 1
        assert "STU-9001" in file_list[0]


@pytest.mark.django_db
def test_report_card_api_endpoints(report_card_setup):
    """Verify ReportCardViewSet generate, list, download, and bulk-zip endpoints."""
    data = report_card_setup
    client = APIClient()
    client.force_authenticate(user=data["admin_user"])

    # 1. Generate single card
    res_gen = client.post(
        "/api/v1/results/report-cards/generate/",
        {"exam_result_id": str(data["exam_res"].id)},
        format="json",
    )
    assert res_gen.status_code == status.HTTP_201_CREATED
    card_id = res_gen.data["id"]

    # 2. List
    res_list = client.get("/api/v1/results/report-cards/")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data["results"]) >= 1

    # 3. Download single PDF
    res_dl = client.get(f"/api/v1/results/report-cards/{card_id}/download/")
    assert res_dl.status_code == status.HTTP_200_OK
    assert res_dl.headers["Content-Type"] == "application/pdf"

    # 4. Bulk zip download
    res_zip = client.post(
        "/api/v1/results/report-cards/bulk_zip/",
        {
            "exam_id": str(data["exam"].id),
            "class_level_id": str(data["class_level"].id),
        },
        format="json",
    )
    assert res_zip.status_code == status.HTTP_200_OK
    assert res_zip.headers["Content-Type"] == "application/zip"
