"""Tests for Result Publication workflow, approvals, and portal visibility."""

from datetime import date, time
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import Role, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.exams.models import Exam, ExamSubject, ExamType, MarkEntry
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.results.models import ExamResult, ExamResultStatus
from apps.results.services import (
    approve_exam_results,
    can_view_exam_result,
    publish_exam_results,
    seed_default_bd_grading_scale,
    tabulate_exam_results,
    unpublish_exam_results,
)
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def pub_setup(db):
    inst = Institution.objects.create(
        name_en="Comilla Zilla School",
        name_bn="কুমিল্লা জিলা স্কুল",
        eiin="108261",
        address_line="Comilla",
        email="comillazilla@edu.bd",
        phone="+8801700000003",
    )
    branch = Branch.objects.create(institution=inst, name="Main")
    session = AcademicSession.objects.create(
        institution=inst,
        name="2026 Session",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Day",
        start_time=time(10, 0),
        end_time=time(16, 0),
    )
    class_level = ClassLevel.objects.create(institution=inst, name="Class 8", order=8)
    section = Section.objects.create(
        institution=inst,
        shift=shift,
        class_level=class_level,
        session=session,
        name="Section B",
    )
    seed_default_bd_grading_scale(inst)

    student = Student.objects.create(
        institution=inst,
        student_id="STU-8001",
        name_en="Sabbir Hasan",
        name_bn="সাব্বির হাসান",
        admission_date="2026-01-01",
        dob="2010-01-01",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=session,
        class_level=class_level,
        section=section,
        shift=shift,
        roll_no=1,
        enrollment_date="2026-01-01",
    )

    exam_type = ExamType.objects.create(institution=inst, name="Mid-Term")
    exam = Exam.objects.create(
        institution=inst,
        name="Mid-Term Examination 2026",
        session=session,
        exam_type=exam_type,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 15),
    )
    exam.target_classes.add(class_level)

    subject = Subject.objects.create(
        institution=inst,
        name_en="General Science",
        name_bn="সাধারণ বিজ্ঞান",
        code="SCI-08",
    )
    es = ExamSubject.objects.create(
        institution=inst,
        exam=exam,
        class_level=class_level,
        subject=subject,
        full_marks=Decimal("100.00"),
        pass_marks=Decimal("33.00"),
        creative_full_marks=Decimal("100.00"),
        creative_pass_marks=Decimal("33.00"),
        mcq_full_marks=Decimal("0.00"),
        mcq_pass_marks=Decimal("0.00"),
        practical_full_marks=Decimal("0.00"),
        practical_pass_marks=Decimal("0.00"),
    )

    MarkEntry.objects.create(
        institution=inst,
        exam_subject=es,
        student=student,
        creative_marks=Decimal("65.00"),
        total_marks=Decimal("65.00"),
    )

    tabulate_exam_results(exam.id)
    exam_res = ExamResult.objects.get(exam=exam, student=student)

    admin_user = make_user(
        username="pub_admin_user",
        institution=inst,
        phone="+8801700111224",
        user_type=UserType.STAFF,
        role="admin",
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    # Student user
    stu_user = make_user(
        username="pub_student_user",
        institution=inst,
        phone="+8801700111225",
        user_type=UserType.STUDENT,
    )
    stu_user.student_profile = student  # type: ignore[attr-defined]
    stu_user.save()
    role_stu, _ = Role.objects.get_or_create(institution=inst, code="student")
    UserRole.objects.get_or_create(user=stu_user, role=role_stu)

    return {
        "inst": inst,
        "exam": exam,
        "student": student,
        "exam_res": exam_res,
        "admin_user": admin_user,
        "stu_user": stu_user,
    }


@pytest.mark.django_db
def test_publication_workflow(pub_setup):
    """Verify approval, publication, and unpublication state transitions."""
    data = pub_setup
    exam = data["exam"]
    exam_res = data["exam_res"]
    stu_user = data["stu_user"]

    # 1. Initially draft: student cannot view
    assert exam_res.status == ExamResultStatus.DRAFT
    assert can_view_exam_result(stu_user, exam_res) is False

    # 2. Approve results
    app_res = approve_exam_results(exam.id, user=data["admin_user"])
    assert app_res["status"] == "approved"
    exam_res.refresh_from_db()
    assert exam_res.status == ExamResultStatus.APPROVED
    assert can_view_exam_result(stu_user, exam_res) is False

    # 3. Publish results
    pub_res = publish_exam_results(
        exam.id,
        user=data["admin_user"],
        is_visible_to_students=True,
        allow_public_search=True,
    )
    assert pub_res["status"] == "published"
    exam_res.refresh_from_db()
    assert exam_res.status == ExamResultStatus.PUBLISHED
    assert can_view_exam_result(stu_user, exam_res) is True

    # 4. Unpublish results
    unpub_res = unpublish_exam_results(exam.id, user=data["admin_user"])
    assert unpub_res["status"] == "unpublished"
    exam_res.refresh_from_db()
    assert exam_res.status == ExamResultStatus.DRAFT
    assert can_view_exam_result(stu_user, exam_res) is False


@pytest.mark.django_db
def test_publication_api_endpoints(pub_setup):
    """Verify ResultPublicationViewSet endpoints."""
    data = pub_setup
    client = APIClient()
    client.force_authenticate(user=data["admin_user"])

    # 1. Approve via API
    res_app = client.post(
        "/api/v1/results/publications/approve/",
        {"exam_id": str(data["exam"].id)},
        format="json",
    )
    assert res_app.status_code == status.HTTP_200_OK

    # 2. Publish via API
    res_pub = client.post(
        "/api/v1/results/publications/publish/",
        {
            "exam_id": str(data["exam"].id),
            "is_visible_to_guardians": True,
            "is_visible_to_students": True,
            "allow_public_search": True,
            "remarks": "Approved by Academic Committee",
        },
        format="json",
    )
    assert res_pub.status_code == status.HTTP_200_OK

    # 3. List
    res_list = client.get("/api/v1/results/publications/")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data["results"]) >= 1
