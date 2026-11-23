from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Period, RoutineSlot, Section, Subject
from apps.accounts.models import User, UserType
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_routine_and_teachers_empty_when_not_enrolled_in_active_session(api_client):
    inst = Institution.objects.create(name_en="Test School", name_bn="টেস্ট স্কুল", eiin="991122")
    branch = Branch.objects.create(institution=inst, name="Main Branch", code="MB01")
    shift = Shift.objects.create(
        institution=inst, branch=branch, name="Morning", start_time="08:00", end_time="13:00"
    )

    # Session 2026 (old) and 2027 (current/active)
    sess_2026 = AcademicSession.objects.create(
        institution=inst,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=False,
    )
    AcademicSession.objects.create(
        institution=inst,
        name="2027",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
        is_current=True,
    )

    # 2026 setup
    cl_2026 = ClassLevel.objects.create(
        institution=inst, session=sess_2026, name="Class 6", code="C06", order=6
    )
    sec_2026 = Section.objects.create(
        institution=inst, class_level=cl_2026, session=sess_2026, shift=shift, name="Section A"
    )
    period = Period.objects.create(
        institution=inst,
        shift=shift,
        name="1st Period",
        order=1,
        start_time="08:00",
        end_time="08:45",
    )
    subject = Subject.objects.create(
        institution=inst, name_en="Bangla", name_bn="বাংলা", code="BAN101"
    )

    teacher_user = User.objects.create_user(
        username="teacher1",
        phone="+8801700000001",
        user_type=UserType.TEACHER,
        institution=inst,
    )

    RoutineSlot.objects.create(
        institution=inst,
        section=sec_2026,
        period=period,
        subject=subject,
        teacher_user=teacher_user,
        weekday=1,
    )

    # Student only enrolled in 2026
    student_user = User.objects.create_user(
        username="student1",
        phone="+8801700000002",
        user_type=UserType.STUDENT,
        institution=inst,
    )
    student = Student.objects.create(
        institution=inst,
        user=student_user,
        student_id="ST-001",
        name_en="Rahim Uddin",
        name_bn="রহিম উদ্দিন",
        dob=date(2012, 1, 1),
        admission_date=date(2026, 1, 1),
        gender="male",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=sess_2026,
        class_level=cl_2026,
        section=sec_2026,
        roll_no=1,
        enrollment_date=date(2026, 1, 1),
        status="active",
    )

    # Authenticate as student
    api_client.force_authenticate(user=student_user)

    # 1. Query routine slots with 2027 active -> must return 0 slots
    resp = api_client.get("/api/v1/academics/routine/")
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 0

    # 2. Query my-teachers with 2027 active -> must return empty list []
    resp_t = api_client.get("/api/v1/academics/sections/my-teachers/")
    assert resp_t.status_code == 200
    assert resp_t.data == []

    # 3. Explicitly querying 2026 session should return the 2026 routine slot
    resp_2026 = api_client.get(
        f"/api/v1/academics/routine/?session={sess_2026.id}&student={student.id}"
    )
    assert resp_2026.status_code == 200
    assert len(resp_2026.data["results"]) == 1
