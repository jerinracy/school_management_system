"""Integration API tests for examination endpoints."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.exams.models import (
    AdmitCard,
    Exam,
    ExamSubject,
    ExamType,
    MarkEntry,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.staff.models import Staff
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka Model College", eiin="332211")


@pytest.fixture
def branch(db, institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main Campus", code="MAIN")


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
def shift(db, institution, branch) -> Shift:
    from datetime import time

    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="Day Shift",
        start_time=time(11, 0),
        end_time=time(16, 30),
    )


@pytest.fixture
def class_level(db, institution) -> ClassLevel:
    return ClassLevel.objects.create(institution=institution, name="Class 10", order=10)


@pytest.fixture
def section(db, institution, class_level, shift, academic_session) -> Section:
    return Section.objects.create(
        institution=institution,
        class_level=class_level,
        shift=shift,
        session=academic_session,
        name="Section A",
    )


@pytest.fixture
def subject(db, institution) -> Subject:
    return Subject.objects.create(
        institution=institution, name_en="English 1st Paper", code="ENG-101"
    )


@pytest.fixture
def student(db, institution, academic_session, class_level, section, shift) -> Student:
    s = Student.objects.create(
        institution=institution,
        student_id="STU-1001",
        name_en="Nafis Iqbal",
        dob="2010-04-12",
        gender="male",
        admission_date="2026-01-01",
    )
    StudentEnrollment.objects.create(
        institution=institution,
        student=s,
        session=academic_session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=1,
        enrollment_date=date(2026, 1, 1),
        status=EnrollmentStatus.ACTIVE,
    )
    return s


def _assign_exam_perms(
    user: User, institution: Institution, role_code: str, codenames: list[str]
) -> None:
    role, _ = Role.objects.get_or_create(institution=institution, code=role_code)
    ct = ContentType.objects.get_for_model(Exam)
    for cname in codenames:
        perm, _ = Permission.objects.get_or_create(
            codename=cname,
            content_type=ct,
            defaults={"name": f"Can {cname}"},
        )
        role.permissions.add(perm)
    UserRole.objects.get_or_create(user=user, role=role)


@pytest.fixture
def admin_user(institution) -> tuple[APIClient, Any]:
    user = make_user(
        username="admin_exam",
        phone="+8801700000091",
        institution=institution,
        role="admin",
    )
    _assign_exam_perms(
        user, institution, "admin_role", ["manage", "view", "enter_marks", "lock_marks"]
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def teacher_user(institution) -> tuple[APIClient, Any, Staff]:
    user = make_user(
        username="teacher_exam",
        phone="+8801700000092",
        institution=institution,
        user_type=UserType.TEACHER,
        role="teacher",
    )
    _assign_exam_perms(user, institution, "teacher_role", ["view", "enter_marks"])
    staff = Staff.objects.create(
        institution=institution,
        user=user,
        employee_id="TCH-301",
        full_name_en="Rezaul Karim",
        phone=str(user.phone),
        dob="1982-01-01",
        gender="male",
        joining_date="2018-01-01",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, staff


@pytest.fixture
def foreign_teacher_user(institution) -> tuple[APIClient, Any, Staff]:
    user = make_user(
        username="foreign_teacher",
        phone="+8801700000093",
        institution=institution,
        user_type=UserType.TEACHER,
        role="teacher",
    )
    _assign_exam_perms(user, institution, "foreign_teacher_role", ["view", "enter_marks"])
    staff = Staff.objects.create(
        institution=institution,
        user=user,
        employee_id="TCH-302",
        full_name_en="Other Teacher",
        phone=str(user.phone),
        dob="1985-05-05",
        gender="male",
        joining_date="2019-01-01",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, staff


@pytest.mark.django_db
def test_exam_crud_and_actions_api(admin_user, institution, academic_session, class_level, student):
    client, user = admin_user

    # 1. Create ExamType
    type_res = client.post(
        "/api/v1/exams/types/",
        {"name": "Pre-Test Exam", "code": "PRE_TEST", "is_board_exam": False},
        format="json",
    )
    assert type_res.status_code == status.HTTP_201_CREATED
    type_id = type_res.data["id"]

    # 2. Create Exam
    exam_res = client.post(
        "/api/v1/exams/exams/",
        {
            "exam_type": type_id,
            "session": str(academic_session.id),
            "name": "Pre-Test Examination 2026",
            "term": "Pre-Test",
            "start_date": "2026-09-01",
            "end_date": "2026-09-15",
            "target_classes": [str(class_level.id)],
        },
        format="json",
    )
    assert exam_res.status_code == status.HTTP_201_CREATED
    exam_id = exam_res.data["id"]

    # 3. Action: Generate Eligibility
    elig_res = client.post(f"/api/v1/exams/exams/{exam_id}/generate_eligibility/")
    assert elig_res.status_code == status.HTTP_200_OK
    assert elig_res.data["total_evaluated"] >= 1

    # 4. Action: Generate Seat Plans
    seat_res = client.post(
        f"/api/v1/exams/exams/{exam_id}/generate_seat_plans/",
        {
            "room_configs": [{"room_number": "101", "bench_count": 10, "seats_per_bench": 2}],
            "interleave": False,
        },
        format="json",
    )
    assert seat_res.status_code == status.HTTP_200_OK
    assert seat_res.data["total_allocated"] >= 1

    # 5. Action: Progress tracker
    prog_res = client.get(f"/api/v1/exams/exams/{exam_id}/progress/")
    assert prog_res.status_code == status.HTTP_200_OK
    assert "subjects_progress" in prog_res.data


@pytest.mark.django_db
def test_mark_entry_bulk_save_and_locking_api(
    admin_user,
    teacher_user,
    foreign_teacher_user,
    institution,
    academic_session,
    class_level,
    subject,
    student,
):
    admin_client, admin = admin_user
    teacher_client, teacher, teacher_staff = teacher_user
    foreign_client, foreign_t, foreign_staff = foreign_teacher_user

    # Setup exam and subject assigned to teacher_staff
    etype = ExamType.objects.create(institution=institution, name="Half-Yearly", code="HY")
    exam = Exam.objects.create(
        institution=institution,
        exam_type=etype,
        session=academic_session,
        name="HY 2026",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 20),
    )
    exam_subj = ExamSubject.objects.create(
        institution=institution,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        creative_full_marks=Decimal("70.00"),
        mcq_full_marks=Decimal("30.00"),
        assigned_teacher=teacher_staff,
    )

    # 1. Assigned teacher submits marks via bulk_save
    payload = {
        "exam_subject_id": str(exam_subj.id),
        "entries": [
            {
                "student_id": str(student.id),
                "creative_marks": "55.00",
                "mcq_marks": "25.00",
                "practical_marks": "0.00",
                "is_absent": False,
            }
        ],
    }
    res = teacher_client.post("/api/v1/exams/mark-entries/bulk_save/", payload, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["saved_count"] == 1

    entry = MarkEntry.objects.get(exam_subject=exam_subj, student=student)
    assert entry.total_marks == Decimal("80.00")

    # 2. Foreign teacher attempts bulk_save -> 403 Forbidden
    foreign_res = foreign_client.post(
        "/api/v1/exams/mark-entries/bulk_save/", payload, format="json"
    )
    assert foreign_res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_207_MULTI_STATUS]
    if foreign_res.status_code == status.HTTP_207_MULTI_STATUS:
        assert len(foreign_res.data["errors"]) > 0

    # 3. Admin locks marks
    lock_res = admin_client.post(
        "/api/v1/exams/mark-entries/lock/", {"exam_subject_id": str(exam_subj.id)}
    )
    assert lock_res.status_code == status.HTTP_200_OK
    exam_subj.refresh_from_db()
    assert exam_subj.is_marks_locked is True

    # 4. Teacher attempts modification while locked -> returns error
    res_locked = teacher_client.post(
        "/api/v1/exams/mark-entries/bulk_save/", payload, format="json"
    )
    assert res_locked.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_207_MULTI_STATUS]

    # 5. Admin unlocks marks
    unlock_res = admin_client.post(
        "/api/v1/exams/mark-entries/unlock/",
        {"exam_subject_id": str(exam_subj.id), "reason": "Authorized correction window"},
    )
    assert unlock_res.status_code == status.HTTP_200_OK
    exam_subj.refresh_from_db()
    assert exam_subj.is_marks_locked is False


@pytest.mark.django_db
def test_admit_card_pdf_download_api(
    admin_user, institution, academic_session, class_level, student
):
    client, user = admin_user
    etype = ExamType.objects.create(institution=institution, name="Annual", code="ANNUAL")
    exam = Exam.objects.create(
        institution=institution,
        exam_type=etype,
        session=academic_session,
        name="Annual Exam 2026",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 20),
    )
    card = AdmitCard.objects.create(
        institution=institution,
        exam=exam,
        student=student,
        card_number="ADM-2026-TEST-00001",
    )

    res = client.get(f"/api/v1/exams/admit-cards/{card.id}/download_pdf/")
    assert res.status_code == status.HTTP_200_OK
    assert res["Content-Type"] == "application/pdf"
    assert len(res.content) > 1000


@pytest.mark.django_db
def test_exam_type_crud_and_validation(admin_user, institution):
    client, user = admin_user

    # 1. Create ExamType with lowercase code
    create_res = client.post(
        "/api/v1/exams/types/",
        {
            "name": "Monthly Class Assessment",
            "code": "mca",
            "is_board_exam": False,
            "description": "Monthly continuous progress test",
        },
        format="json",
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    type_id = create_res.data["id"]
    assert create_res.data["code"] == "MCA"
    assert create_res.data["name"] == "Monthly Class Assessment"

    # 2. Reject duplicate code in same institution
    dup_res = client.post(
        "/api/v1/exams/types/",
        {
            "name": "Another Assessment",
            "code": "MCA",
            "is_board_exam": False,
        },
        format="json",
    )
    assert dup_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "code" in dup_res.data.get("details", dup_res.data)

    # 3. Update ExamType
    patch_res = client.patch(
        f"/api/v1/exams/types/{type_id}/",
        {"description": "Updated monthly evaluation protocol"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.data["description"] == "Updated monthly evaluation protocol"

    # 4. List ExamTypes
    list_res = client.get("/api/v1/exams/types/")
    assert list_res.status_code == status.HTTP_200_OK
    results = list_res.data.get("results", list_res.data)
    assert any(item["id"] == type_id for item in results)

    # 5. Delete ExamType
    del_res = client.delete(f"/api/v1/exams/types/{type_id}/")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT
    assert not ExamType.objects.filter(id=type_id).exists()
