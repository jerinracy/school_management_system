from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import User, UserType
from apps.guardians.models import Guardian, StudentGuardian
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.mark.django_db
def test_my_children_session_scoping_and_active_enrollment():
    client = APIClient()
    inst = Institution.objects.create(name_en="Demo School", name_bn="ডেমো স্কুল", eiin="991122")
    branch = Branch.objects.create(institution=inst, name="Main Campus")
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Morning Shift",
        start_time="08:00:00",
        end_time="13:00:00",
    )
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

    cl = ClassLevel.objects.create(institution=inst, name="Class 5", order=5)
    sec = Section.objects.create(
        institution=inst, class_level=cl, name="A", session=sess_2026, shift=shift
    )

    student = Student.objects.create(
        institution=inst,
        student_id="ST-001",
        name_en="Child One",
        name_bn="চাইল্ড এক",
        dob=date(2015, 5, 10),
        admission_date=date(2026, 1, 1),
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=sess_2026,
        class_level=cl,
        section=sec,
        roll_no=1,
        status="active",
        enrollment_date=date(2026, 1, 1),
    )

    guardian_user = User.objects.create_user(
        username="+8801700000001",
        phone="+8801700000001",
        password="password123",
        institution=inst,
        user_type=UserType.GUARDIAN,
    )
    guardian = Guardian.objects.create(
        institution=inst,
        user=guardian_user,
        phone="+8801700000001",
        name_en="Parent One",
        name_bn="অভিভাবক এক",
    )
    StudentGuardian.objects.create(
        institution=inst,
        student=student,
        guardian=guardian,
        relation="father",
        is_primary=True,
    )

    client.force_authenticate(user=guardian_user)

    # 1. With sess_2027 active and student only in sess_2026:
    res = client.get("/api/v1/guardians/guardians/my-children/")
    assert res.status_code == 200
    assert len(res.data) == 1
    ward = res.data[0]
    assert ward["is_enrolled_in_active_session"] is False
    assert ward["active_session_name"] == "2027"
    assert ward["previous_session_name"] == "2026"
    assert ward["enrollment"] is None

    # 2. Querying explicitly for 2026 session:
    res_2026 = client.get(f"/api/v1/guardians/guardians/my-children/?session={sess_2026.id}")
    assert res_2026.status_code == 200
    ward_2026 = res_2026.data[0]
    assert ward_2026["is_enrolled_in_active_session"] is True
    assert ward_2026["enrollment"]["session_name"] == "2026"
    assert ward_2026["enrollment"]["class_name"] == "Class 5"
