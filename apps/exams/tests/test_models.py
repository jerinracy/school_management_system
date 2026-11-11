"""Unit tests for Examination models, constraints, and validation."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassLevel, Subject
from apps.exams.models import (
    Exam,
    ExamStatus,
    ExamSubject,
    ExamType,
    MarkEntry,
)
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka Model College", eiin="332211")


@pytest.fixture
def academic_session(db, institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def class_level(db, institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 9",
        order=9,
    )


@pytest.fixture
def subject(db, institution) -> Subject:
    return Subject.objects.create(
        institution=institution,
        name_en="Physics",
        name_bn="পদার্থবিজ্ঞান",
        code="PHY-101",
    )


@pytest.fixture
def exam_type(db, institution) -> ExamType:
    return ExamType.objects.create(
        institution=institution,
        name="Half-Yearly Examination",
        code="HY",
        is_board_exam=False,
    )


@pytest.fixture
def exam(db, institution, exam_type, academic_session, class_level) -> Exam:
    exam_obj = Exam.objects.create(
        institution=institution,
        exam_type=exam_type,
        session=academic_session,
        name="Half-Yearly Examination 2026",
        term="Half-Yearly",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20),
        status=ExamStatus.SCHEDULED,
    )
    exam_obj.target_classes.add(class_level)
    return exam_obj


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-901",
        name_en="Kamrul Islam",
        name_bn="কামরুল ইসলাম",
        dob="2010-05-15",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.mark.django_db
def test_exam_type_and_exam_creation(exam_type, exam):
    assert str(exam_type) == "Half-Yearly Examination (HY)"
    assert "Half-Yearly Examination 2026" in str(exam)
    assert exam.status == ExamStatus.SCHEDULED


@pytest.mark.django_db
def test_exam_date_validation(exam_type, academic_session, institution):
    invalid_exam = Exam(
        institution=institution,
        exam_type=exam_type,
        session=academic_session,
        name="Invalid Date Exam",
        start_date=date(2026, 6, 20),
        end_date=date(2026, 6, 10),  # earlier than start
    )
    with pytest.raises(ValidationError):
        invalid_exam.clean()


@pytest.mark.django_db
def test_exam_subject_component_validation(institution, exam, class_level, subject):
    # Valid component sum: 70 + 30 + 0 = 100
    es = ExamSubject(
        institution=institution,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        creative_full_marks=Decimal("70.00"),
        mcq_full_marks=Decimal("30.00"),
        practical_full_marks=Decimal("0.00"),
    )
    es.clean()  # should not raise
    es.save()
    assert str(es) == "Half-Yearly Examination 2026 - Class 9 - Physics"

    # Invalid component sum: 70 + 20 + 0 = 90 != 100
    invalid_es = ExamSubject(
        institution=institution,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        creative_full_marks=Decimal("70.00"),
        mcq_full_marks=Decimal("20.00"),
        practical_full_marks=Decimal("0.00"),
    )
    with pytest.raises(ValidationError):
        invalid_es.clean()


@pytest.mark.django_db
def test_mark_entry_calculate_total(institution, exam, class_level, subject, student):
    es = ExamSubject.objects.create(
        institution=institution,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        creative_full_marks=Decimal("70.00"),
        mcq_full_marks=Decimal("30.00"),
    )

    # 1. Normal marks
    mark = MarkEntry.objects.create(
        institution=institution,
        exam_subject=es,
        student=student,
        creative_marks=Decimal("55.50"),
        mcq_marks=Decimal("25.00"),
        practical_marks=Decimal("0.00"),
    )
    assert mark.calculate_total() == Decimal("80.50")

    # 2. Absent student
    absent_mark = MarkEntry(
        institution=institution,
        exam_subject=es,
        student=student,
        is_absent=True,
    )
    assert absent_mark.calculate_total() == Decimal("0.00")
