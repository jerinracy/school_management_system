"""Unit tests for Results and Grading Engine models."""

from datetime import time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassLevel, Section, Subject
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.results.models import (
    GradeTier,
    GradingScale,
    ScaleType,
    StudentOptionalSubject,
)
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Residential Model College",
        name_bn="ঢাকা রেসিডেন্সিয়াল মডেল কলেজ",
        eiin="108256",
        address_line="Mirpur Road, Dhaka",
        email="drmc@edu.bd",
        phone="+8801700000000",
    )


@pytest.fixture
def academic_session(institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026 Academic Year",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )


@pytest.fixture
def class_level(institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 9",
        order=9,
        code="CLS-9",
    )


@pytest.fixture
def branch(institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main Campus", code="MAIN")


@pytest.fixture
def shift(institution, branch) -> Shift:
    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="Day Shift",
        start_time=time(11, 0),
        end_time=time(16, 30),
    )


@pytest.fixture
def section(institution, class_level, shift, academic_session) -> Section:
    return Section.objects.create(
        institution=institution,
        class_level=class_level,
        shift=shift,
        session=academic_session,
        name="Section A",
        capacity=50,
    )


@pytest.fixture
def student(institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-2026-001",
        name_en="Tanvir Ahmed",
        name_bn="তানভীর আহমেদ",
        dob="2010-05-15",
        admission_date="2026-01-01",
        gender="male",
        religion="islam",
        blood_group="b_positive",
    )


@pytest.fixture
def student_enrollment(
    institution, student, academic_session, class_level, section
) -> StudentEnrollment:
    return StudentEnrollment.objects.create(
        institution=institution,
        student=student,
        session=academic_session,
        class_level=class_level,
        section=section,
        roll_no=1,
        enrollment_date="2026-01-01",
    )


@pytest.mark.django_db
def test_grading_scale_and_tiers_creation(institution):
    """Test creating a GradingScale and nested GradeTiers."""
    scale = GradingScale.objects.create(
        institution=institution,
        name="BD National Curriculum (GPA 5.0)",
        scale_type=ScaleType.GPA_5,
        max_gpa=Decimal("5.00"),
        pass_gpa=Decimal("1.00"),
        is_default=True,
    )
    assert scale.scale_type == ScaleType.GPA_5
    assert (
        str(scale) == "BD National Curriculum (GPA 5.0) (Bangladesh National Curriculum (GPA 5.0))"
    )

    tier_a_plus = GradeTier.objects.create(
        institution=institution,
        scale=scale,
        letter_grade="A+",
        grade_point=Decimal("5.00"),
        min_percentage=Decimal("80.00"),
        max_percentage=Decimal("100.00"),
        remarks_en="Outstanding",
        remarks_bn="অসাধারণ",
    )
    assert str(tier_a_plus) == "A+ (5.00) [80.00% - 100.00%]"


@pytest.mark.django_db
def test_only_one_default_grading_scale(institution):
    """Test that only one default grading scale can be marked per institution."""
    GradingScale.objects.create(
        institution=institution,
        name="Scale 1",
        is_default=True,
    )
    scale2 = GradingScale(
        institution=institution,
        name="Scale 2",
        is_default=True,
    )
    with pytest.raises(ValidationError):
        scale2.clean()


@pytest.mark.django_db
def test_student_optional_subject_assignment(institution, student, academic_session, class_level):
    """Test designating a 4th / optional subject for a student."""
    subj = Subject.objects.create(
        institution=institution,
        name_en="Higher Mathematics",
        name_bn="উচ্চতর গণিত",
        code="HM-101",
    )
    opt = StudentOptionalSubject.objects.create(
        institution=institution,
        student=student,
        session=academic_session,
        class_level=class_level,
        subject=subj,
    )
    assert str(opt) == f"{student.student_id} - 4th Subject: Higher Mathematics"
