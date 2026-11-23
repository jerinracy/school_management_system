"""Tests for session-scoped chat threads."""

from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.communications.models import ChatThread
from apps.guardians.models import Guardian
from apps.institutions.models import AcademicSession, Institution
from apps.staff.models import Staff
from apps.students.models import Student


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model School",
        name_bn="ঢাকা মডেল স্কুল",
        eiin="100201",
    )


@pytest.fixture
def session_2026(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def session_2025(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        is_current=False,
    )


@pytest.fixture
def teacher_user(db: None, institution: Institution) -> User:
    return User.objects.create_user(
        username="teacher_chat_user",
        phone="+8801711000002",
        email="teacher@school.edu.bd",
        password="TeacherPass123!",
        user_type="teacher",
        institution=institution,
    )


@pytest.fixture
def teacher_staff(institution: Institution, teacher_user: User) -> Staff:
    return Staff.objects.create(
        institution=institution,
        user=teacher_user,
        employee_id="TCH-2026-001",
        full_name_en="Mohammad Ali",
        full_name_bn="মোহাম্মদ আলী",
        email="teacher@school.edu.bd",
        phone="+8801711000002",
        gender="male",
        dob=date(1985, 1, 1),
        joining_date=date(2020, 1, 1),
    )


@pytest.fixture
def guardian(institution: Institution) -> Guardian:
    return Guardian.objects.create(
        institution=institution,
        name_en="Rahim Uddin",
        phone="+8801811000003",
    )


@pytest.fixture
def student(institution: Institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STD-2026-001",
        name_en="Karim Rahim",
        admission_date=date(2026, 1, 1),
        dob=date(2012, 5, 10),
        gender="male",
    )


@pytest.mark.django_db
class TestSessionChatIsolation:
    def test_chat_threads_scoped_to_session(
        self,
        institution: Institution,
        session_2026: AcademicSession,
        session_2025: AcademicSession,
        teacher_user: User,
        teacher_staff: Staff,
        guardian: Guardian,
        student: Student,
    ):
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        # Thread in 2026
        thread_2026 = ChatThread.objects.create(
            institution=institution,
            session=session_2026,
            teacher=teacher_staff,
            guardian=guardian,
            student=student,
            subject="Academic progress in 2026",
        )

        # Thread in 2025
        thread_2025 = ChatThread.objects.create(
            institution=institution,
            session=session_2025,
            teacher=teacher_staff,
            guardian=guardian,
            student=student,
            subject="Previous year performance 2025",
        )

        # Default query returns active session (2026) threads
        res = client.get("/api/v1/communications/chat/threads/")
        assert res.status_code == status.HTTP_200_OK
        ids = [t["id"] for t in res.data["results"]]
        assert str(thread_2026.id) in ids
        assert str(thread_2025.id) not in ids

        # Querying specifically for 2025 session returns only 2025 thread
        res_2025 = client.get(f"/api/v1/communications/chat/threads/?session={session_2025.id}")
        assert res_2025.status_code == status.HTTP_200_OK
        ids_2025 = [t["id"] for t in res_2025.data["results"]]
        assert str(thread_2025.id) in ids_2025
        assert str(thread_2026.id) not in ids_2025
