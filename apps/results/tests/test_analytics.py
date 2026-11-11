"""Tests for weak-student diagnostics, promotion feeds, and public search."""

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
from apps.results.models import CumulativeResult
from apps.results.services import (
    get_promotion_eligibility_feed,
    get_weak_students_analytics,
    publish_exam_results,
    seed_default_bd_grading_scale,
    tabulate_exam_results,
)
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def analytics_setup(db):
    inst = Institution.objects.create(
        name_en="Barisal Zilla School",
        name_bn="বরিশাল জিলা স্কুল",
        eiin="108262",
        address_line="Barisal",
        email="barisal@edu.bd",
        phone="+8801700000004",
    )
    branch = Branch.objects.create(institution=inst, name="Main")
    session = AcademicSession.objects.create(
        institution=inst,
        name="2026 Academic Year",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Morning",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )
    class_level = ClassLevel.objects.create(institution=inst, name="Class 7", order=7)
    section = Section.objects.create(
        institution=inst,
        shift=shift,
        class_level=class_level,
        session=session,
        name="Section A",
    )
    seed_default_bd_grading_scale(inst)

    # Student 1: Good (A)
    s1 = Student.objects.create(
        institution=inst,
        student_id="STU-7001",
        name_en="Al Amin",
        admission_date="2026-01-01",
        dob="2010-01-01",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=s1,
        session=session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=1,
        enrollment_date="2026-01-01",
    )

    # Student 2: Weak / Failed (F)
    s2 = Student.objects.create(
        institution=inst,
        student_id="STU-7002",
        name_en="Bijoy Roy",
        admission_date="2026-01-01",
        dob="2010-01-01",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=s2,
        session=session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=2,
        enrollment_date="2026-01-01",
    )

    exam_type = ExamType.objects.create(institution=inst, name="Annual")
    exam = Exam.objects.create(
        institution=inst,
        name="Annual Exam 2026",
        session=session,
        exam_type=exam_type,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 15),
    )
    exam.target_classes.add(class_level)

    math = Subject.objects.create(institution=inst, name_en="Math", code="M-7")
    es = ExamSubject.objects.create(
        institution=inst,
        exam=exam,
        class_level=class_level,
        subject=math,
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_full_marks=Decimal("100.00"),
        creative_pass_marks=Decimal("33.00"),
        mcq_full_marks=Decimal("0.00"),
        mcq_pass_marks=Decimal("0.00"),
        practical_full_marks=Decimal("0.00"),
        practical_pass_marks=Decimal("0.00"),
    )

    # S1 passes (75 marks)
    MarkEntry.objects.create(
        institution=inst,
        exam_subject=es,
        student=s1,
        creative_marks=Decimal("75.00"),
        total_marks=Decimal("75.00"),
    )
    # S2 fails (20 marks)
    MarkEntry.objects.create(
        institution=inst,
        exam_subject=es,
        student=s2,
        creative_marks=Decimal("20.00"),
        total_marks=Decimal("20.00"),
    )

    tabulate_exam_results(exam.id)

    # Attendance for session
    for day in range(1, 11):
        # S1 attends all
        DailyAttendance.objects.create(
            institution=inst,
            user_type="student",
            student=s1,
            date=date(2026, 1, day),
            status=AttendanceStatus.PRESENT,
        )
        # S2 attends 2 days
        DailyAttendance.objects.create(
            institution=inst,
            user_type="student",
            student=s2,
            date=date(2026, 1, day),
            status=AttendanceStatus.PRESENT if day <= 2 else AttendanceStatus.ABSENT,
        )

    admin_user = make_user(
        username="analytics_admin_user",
        institution=inst,
        phone="+8801700111226",
        user_type=UserType.STAFF,
        role="admin",
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    return {
        "inst": inst,
        "session": session,
        "class_level": class_level,
        "exam": exam,
        "s1": s1,
        "s2": s2,
        "admin_user": admin_user,
    }


@pytest.mark.django_db
def test_get_weak_students_analytics(analytics_setup):
    """Verify weak-student analytics flags failing students and groups failed subjects."""
    data = analytics_setup
    analytics = get_weak_students_analytics(exam_id=data["exam"].id)

    assert analytics["total_students"] == 2
    assert analytics["weak_student_count"] == 1
    assert analytics["students"][0]["student_id"] == "STU-7002"
    assert len(analytics["subject_failure_frequencies"]) == 1
    assert analytics["subject_failure_frequencies"][0]["subject_name"] == "Math"


@pytest.mark.django_db
def test_get_promotion_eligibility_feed(analytics_setup):
    """Verify promotion recommendations based on CGPA and attendance."""
    data = analytics_setup
    # Create mock cumulative results
    CumulativeResult.objects.create(
        institution=data["inst"],
        session=data["session"],
        class_level=data["class_level"],
        student=data["s1"],
        enrollment=data["s1"].enrollments.first(),
        cumulative_gpa=Decimal("4.00"),
        cumulative_grade="A",
        is_passed=True,
    )
    CumulativeResult.objects.create(
        institution=data["inst"],
        session=data["session"],
        class_level=data["class_level"],
        student=data["s2"],
        enrollment=data["s2"].enrollments.first(),
        cumulative_gpa=Decimal("0.00"),
        cumulative_grade="F",
        is_passed=False,
    )

    feed = get_promotion_eligibility_feed(
        session_id=data["session"].id,
        class_level_id=data["class_level"].id,
        min_cgpa=Decimal("2.00"),
        min_attendance_pct=Decimal("70.00"),
    )

    assert feed["total_evaluated"] == 2
    assert feed["promoted_count"] == 1
    assert feed["eligible"][0]["student_id"] == "STU-7001"
    assert feed["retained_count"] == 1
    assert feed["retained"][0]["student_id"] == "STU-7002"


@pytest.mark.django_db
def test_public_result_search_endpoint(analytics_setup):
    """Verify public rate-limited student result lookup."""
    data = analytics_setup
    client = APIClient()

    # 1. When not published or public search disallowed: 403 Forbidden
    res_deny = client.get(
        "/api/v1/results/public-search/",
        {"exam_id": str(data["exam"].id), "student_id": "STU-7001"},
    )
    assert res_deny.status_code == status.HTTP_403_FORBIDDEN

    # 2. Publish with public search allowed
    publish_exam_results(
        data["exam"].id,
        user=data["admin_user"],
        allow_public_search=True,
    )

    # 3. Lookup by student_id
    res_ok = client.get(
        "/api/v1/results/public-search/",
        {"exam_id": str(data["exam"].id), "student_id": "STU-7001"},
    )
    assert res_ok.status_code == status.HTTP_200_OK
    assert res_ok.data["final_gpa"] == "4.00"

    # 4. Lookup by roll_no
    res_roll = client.get(
        "/api/v1/results/public-search/",
        {"exam_id": str(data["exam"].id), "roll_no": "1"},
    )
    assert res_roll.status_code == status.HTTP_200_OK
    assert res_roll.data["student_code"] == "STU-7001"
