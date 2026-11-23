from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import Role, UserRole, UserType
from apps.accounts.test_helpers import api_client_as, make_user
from apps.guardians.models import Guardian, StudentGuardian
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment

User = get_user_model()


@pytest.fixture
def test_setup(db):
    inst = Institution.objects.create(name_en="Scoping Academy", eiin="991122")
    branch = Branch.objects.create(institution=inst, name="Main Campus")
    shift = Shift.objects.create(
        institution=inst, branch=branch, name="Morning", start_time="08:00", end_time="13:00"
    )

    session_2026 = AcademicSession.objects.create(
        institution=inst,
        name="Academic Year 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )

    session_2027 = AcademicSession.objects.create(
        institution=inst,
        name="Academic Year 2027",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
        is_current=False,
    )

    class_6 = ClassLevel.objects.create(institution=inst, name="Class 6", code="C6", order=6)
    section_padma = Section.objects.create(
        institution=inst, class_level=class_6, shift=shift, session=session_2026, name="Padma"
    )

    # Student 1 enrolled in 2026
    student_user = User.objects.create_user(
        username="student1",
        phone="+8801711112233",
        password="TestPassword123!",
        user_type="student",
        institution=inst,
    )
    student1 = Student.objects.create(
        institution=inst,
        user=student_user,
        student_id="STU-2026-001",
        name_en="Tanvir Ahmed",
        gender="male",
        dob=date(2012, 5, 10),
        admission_date=date(2026, 1, 1),
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student1,
        session=session_2026,
        class_level=class_6,
        section=section_padma,
        roll_no=1,
        enrollment_date=date(2026, 1, 1),
        status=EnrollmentStatus.ACTIVE,
    )

    # Guardian for student 1
    guardian = Guardian.objects.create(
        institution=inst,
        name_en="Mr. Ahmed",
        phone="+8801799998877",
    )
    StudentGuardian.objects.create(
        institution=inst,
        student=student1,
        guardian=guardian,
        relation="father",
        is_primary=True,
    )

    # Admin user
    # Permissions and Admin user
    ct_stu = ContentType.objects.get_for_model(Student)
    p_stu_view, _ = Permission.objects.get_or_create(
        codename="view", content_type=ct_stu, defaults={"name": "Can view students"}
    )
    p_stu_manage, _ = Permission.objects.get_or_create(
        codename="manage", content_type=ct_stu, defaults={"name": "Can manage students"}
    )
    ct_guard = ContentType.objects.get_for_model(Guardian)
    p_guard_view, _ = Permission.objects.get_or_create(
        codename="view", content_type=ct_guard, defaults={"name": "Can view guardians"}
    )

    admin_user = make_user(
        username="admin_scoping",
        institution=inst,
        user_type=UserType.ADMIN,
    )
    role = Role.objects.create(institution=inst, name="Admin", code="admin")
    role.permissions.add(p_stu_view, p_stu_manage, p_guard_view)
    UserRole.objects.create(user=admin_user, role=role)
    admin_user.is_staff = True
    admin_user.save(update_fields=["is_staff"])

    return {
        "institution": inst,
        "session_2026": session_2026,
        "session_2027": session_2027,
        "student1": student1,
        "student_user": student_user,
        "guardian": guardian,
        "admin_user": admin_user,
    }


def test_student_list_defaults_to_active_session(test_setup):
    """Student list defaults to the active session (2026), returning student1."""
    admin_client = api_client_as(test_setup["admin_user"])
    res = admin_client.get("/api/v1/students/")
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["id"] == str(test_setup["student1"].id)
    assert res.data["results"][0]["is_enrolled_in_active_session"] is True


def test_student_list_on_new_activated_session(test_setup):
    """When a new session (2027) is activated, student list returns 0 until enrolled."""
    admin_client = api_client_as(test_setup["admin_user"])

    # Activate 2027
    s26 = test_setup["session_2026"]
    s27 = test_setup["session_2027"]
    s26.is_current = False
    s26.save()
    s27.is_current = True
    s27.save()

    # Query without session param: defaults to active (2027)
    res = admin_client.get("/api/v1/students/")
    assert res.status_code == 200
    assert res.data["count"] == 0

    # Query with header X-Academic-Session pointing to 2026: returns student1
    res_26 = admin_client.get("/api/v1/students/", HTTP_X_ACADEMIC_SESSION=str(s26.id))
    assert res_26.status_code == 200
    assert res_26.data["count"] == 1

    # Query with ?session=all: returns student1
    res_all = admin_client.get("/api/v1/students/?session=all")
    assert res_all.status_code == 200
    assert res_all.data["count"] == 1


def test_guardian_list_session_scoping(test_setup):
    """Guardians are filtered based on students enrolled in the active/selected session."""
    admin_client = api_client_as(test_setup["admin_user"])

    # 2026 is active -> guardian of student1 is returned
    res = admin_client.get("/api/v1/guardians/guardians/")
    assert res.status_code == 200
    assert res.data["count"] == 1

    # 2027 is selected -> no students enrolled, so 0 guardians
    s27 = test_setup["session_2027"]
    res_27 = admin_client.get(f"/api/v1/guardians/guardians/?session={s27.id}")
    assert res_27.status_code == 200
    assert res_27.data["count"] == 0


def test_student_me_option_a_login_sync(test_setup):
    """Old session student user can still log in; me returns is_enrolled_in_active_session."""
    student_client = api_client_as(test_setup["student_user"])

    # In 2026 (active), student is enrolled
    res = student_client.get("/api/v1/students/me/")
    assert res.status_code == 200
    assert res.data["is_enrolled_in_active_session"] is True
    assert res.data["active_enrollment"] is not None

    # Switch active session to 2027
    s26 = test_setup["session_2026"]
    s27 = test_setup["session_2027"]
    s26.is_current = False
    s26.save()
    s27.is_current = True
    s27.save()

    # In 2027 (active), student can still log in and call /me/, but enrollment reflects new session
    res2 = student_client.get("/api/v1/students/me/")
    assert res2.status_code == 200
    assert res2.data["is_enrolled_in_active_session"] is False
    assert res2.data["active_enrollment"] is None
