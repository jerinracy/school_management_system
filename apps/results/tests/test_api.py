"""Integration tests for Results and Grading Engine REST API endpoints."""

from datetime import date, time
from decimal import Decimal
from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, ClassSubject, Section, Subject
from apps.accounts.models import Role, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.exams.models import Exam, ExamSubject, ExamType, MarkEntry
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.results.models import ExamResult, ScaleType
from apps.students.models import Student, StudentEnrollment


def _assign_result_perms(
    user: Any, institution: Institution, role_code: str, codenames: list[str]
) -> None:
    role, _ = Role.objects.get_or_create(
        institution=institution,
        code=role_code,
    )
    ct = ContentType.objects.get_for_model(ExamResult)
    for code in codenames:
        perm, _ = Permission.objects.get_or_create(
            codename=code,
            content_type=ct,
            defaults={"name": f"Can {code} results"},
        )
        role.permissions.add(perm)
    UserRole.objects.get_or_create(user=user, role=role)


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Residential Model College",
        name_bn="ঢাকা রেসিডেন্সিয়াল মডেল কলেজ",
        eiin="108258",
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
        name="Class 10",
        order=10,
        code="CLS-10",
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


@pytest.fixture
def admin_user(institution) -> tuple[APIClient, Any]:
    user = make_user(
        username="admin_user",
        phone="+8801700000091",
        institution=institution,
        user_type=UserType.ADMIN,
        role="principal",
    )
    _assign_result_perms(
        user, institution, "admin_role", ["view", "manage", "calculate", "publish"]
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def exam_setup(institution, academic_session, class_level, student, student_enrollment):
    exam_type = ExamType.objects.create(
        institution=institution,
        name="Annual Examination",
        code="ANNUAL",
    )
    exam = Exam.objects.create(
        institution=institution,
        name="Annual Exam 2026",
        exam_type=exam_type,
        session=academic_session,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 20),
        status="marks_entry",
    )
    exam.target_classes.add(class_level)

    subject = Subject.objects.create(
        institution=institution,
        name_en="Mathematics",
        name_bn="গণিত",
        code="MATH-101",
    )
    ClassSubject.objects.create(
        institution=institution,
        class_level=class_level,
        session=academic_session,
        subject=subject,
    )
    exam_subject = ExamSubject.objects.create(
        institution=institution,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_full_marks=Decimal("70.00"),
        creative_pass_marks=Decimal("23.00"),
        mcq_full_marks=Decimal("30.00"),
        mcq_pass_marks=Decimal("10.00"),
    )

    # Enter marks for student (CQ 60 + MCQ 25 = 85 -> Grade A+ / GP 5.0)
    MarkEntry.objects.create(
        institution=institution,
        exam_subject=exam_subject,
        student=student,
        creative_marks=Decimal("60.00"),
        mcq_marks=Decimal("25.00"),
        practical_marks=Decimal("0.00"),
        total_marks=Decimal("85.00"),
    )

    return exam, exam_subject, student


@pytest.mark.django_db
def test_seed_bd_defaults_api(admin_user):
    """Test /api/v1/results/grading-scales/seed_bd_defaults/ endpoint."""
    client, user = admin_user
    url = "/api/v1/results/grading-scales/seed_bd_defaults/"
    response = client.post(url)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "BD National Curriculum (GPA 5.0)"
    assert data["scale_type"] == ScaleType.GPA_5
    assert len(data["tiers"]) == 7


@pytest.mark.django_db
def test_calculate_exam_results_api(admin_user, exam_setup):
    """Test /api/v1/results/exam-results/calculate/ endpoint."""
    client, user = admin_user
    exam, exam_subject, student = exam_setup

    url = "/api/v1/results/exam-results/calculate/"
    payload = {"exam_id": str(exam.id)}
    response = client.post(url, data=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["passed_count"] == 1
    assert data["failed_count"] == 0

    # Verify ExamResult was generated
    res = ExamResult.objects.get(exam=exam, student=student)
    assert res.final_gpa == Decimal("5.00")
    assert res.final_grade == "A+"
    assert res.is_passed is True
    assert res.class_position == 1


@pytest.mark.django_db
def test_exam_summary_api(admin_user, exam_setup):
    """Test /api/v1/results/exam-results/summary/ endpoint."""
    client, user = admin_user
    exam, exam_subject, student = exam_setup

    # First calculate
    client.post("/api/v1/results/exam-results/calculate/", data={"exam_id": str(exam.id)})

    # Then fetch summary
    url = f"/api/v1/results/exam-results/summary/?exam_id={exam.id}"
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_students"] == 1
    assert data["passed_count"] == 1
    assert data["gpa_5_count"] == 1
    assert float(data["pass_percentage"]) == 100.0
    assert data["gpa_distribution"] == {"A+": 1}
