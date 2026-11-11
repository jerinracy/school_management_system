"""Tests for Excel bulk student import."""

import io
from datetime import date

import openpyxl
import pytest

from apps.academics.models import ClassLevel, Section
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment
from apps.students.services import import_students_from_excel


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা হাই স্কুল",
        name_en="Dhaka High School",
        eiin="134568",
    )


@pytest.fixture
def branch(institution) -> Branch:
    return Branch.objects.create(
        institution=institution,
        name="Main Campus",
        code="MAIN",
    )


@pytest.fixture
def shift(branch) -> Shift:
    return Shift.objects.create(
        institution=branch.institution,
        branch=branch,
        name="morning",
        start_time="08:00",
        end_time="12:00",
    )


@pytest.fixture
def session(institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def class_level(institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 8",
        code="CLS8",
        order=8,
    )


@pytest.fixture
def section(class_level, session, shift) -> Section:
    return Section.objects.create(
        institution=class_level.institution,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Padma",
    )


def create_excel_bytes(rows: list[list[str]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.django_db
class TestBulkImport:
    def test_dry_run_validation_success_and_commit(
        self, institution, session, class_level, section
    ):
        header = [
            "student_id",
            "name_en",
            "name_bn",
            "dob",
            "gender",
            "session_name",
            "class_code",
            "section_name",
            "roll_no",
            "birth_reg_no",
            "phone",
        ]
        row1 = [
            "2026080001",
            "Arafat Hossain",
            "আরাফাত হোসেন",
            "2011-04-10",
            "male",
            "2026",
            "CLS8",
            "Padma",
            "1",
            "20111234567890123",
            "01711223344",
        ]
        row2 = [
            "2026080002",
            "Sadia Sultana",
            "সাদিয়া সুলতানা",
            "2011-06-15",
            "female",
            "2026",
            "CLS8",
            "Padma",
            "2",
            "20111234567890124",
            "01811223344",
        ]

        excel_bytes = create_excel_bytes([header, row1, row2])

        # 1. Dry run
        dry_res = import_students_from_excel(
            institution_id=institution.id,
            file_bytes=excel_bytes,
            dry_run=True,
        )
        assert dry_res["success"] is True
        assert dry_res["valid_count"] == 2
        assert dry_res["error_count"] == 0
        assert Student.objects.count() == 0

        # 2. Real commit
        commit_res = import_students_from_excel(
            institution_id=institution.id,
            file_bytes=excel_bytes,
            dry_run=False,
        )
        assert commit_res["success"] is True
        assert commit_res["created_count"] == 2
        assert Student.objects.filter(institution=institution).count() == 2
        assert StudentEnrollment.objects.filter(institution=institution).count() == 2

    def test_dry_run_reports_row_errors(self, institution, session, class_level, section):
        header = [
            "student_id",
            "name_en",
            "name_bn",
            "dob",
            "gender",
            "session_name",
            "class_code",
            "section_name",
            "roll_no",
            "birth_reg_no",
        ]
        # Invalid birth_reg_no (<17 digits), invalid dob, non-existent section
        bad_row = [
            "2026080099",
            "Bad Student",
            "ভুল শিক্ষার্থী",
            "invalid-date",
            "alien",
            "2026",
            "CLS8",
            "NonExistentSection",
            "not-a-number",
            "123",
        ]

        excel_bytes = create_excel_bytes([header, bad_row])

        res = import_students_from_excel(
            institution_id=institution.id,
            file_bytes=excel_bytes,
            dry_run=True,
        )
        assert res["success"] is False
        assert res["error_count"] == 1
        errors = res["errors"][0]["errors"]
        assert any("dob" in err.lower() for err in errors)
        assert any("gender" in err.lower() for err in errors)
        assert any("section" in err.lower() for err in errors)
        assert any("roll" in err.lower() for err in errors)
        assert any("17 digits" in err.lower() for err in errors)
