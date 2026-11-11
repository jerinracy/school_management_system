"""API integration tests for Fee Management ViewSets, permissions, and reports."""

from datetime import time
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import Role, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FeeType,
    RecurrenceType,
    StudentWaiver,
    WaiverApprovalStatus,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def api_fee_setup(db: None) -> dict:
    client = APIClient()
    inst = Institution.objects.create(name_en="API Fee School", name_bn="এপিআই ফি স্কুল")
    branch = Branch.objects.create(institution=inst, name="Campus A")
    session = AcademicSession.objects.create(
        institution=inst,
        name="Session 2026",
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
    class_level = ClassLevel.objects.create(institution=inst, name="Class 6", code="C6", order=6)
    section = Section.objects.create(
        institution=inst,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Section A",
    )

    # 1. Admin User
    admin_user = make_user(
        username="fee_admin",
        institution=inst,
        phone="+8801700111999",
    )
    admin_user.is_superuser = True
    admin_user.save()

    # 2. Student User & Profile
    student = Student.objects.create(
        institution=inst,
        student_id="STU-API-001",
        name_en="Hasibul Hasan",
        name_bn="হাসিবুল হাসান",
        admission_date="2026-01-01",
        dob="2013-02-14",
    )
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=session,
        class_level=class_level,
        section=section,
        roll_no=1,
        enrollment_date="2026-01-01",
    )
    stu_user = make_user(
        username="fee_student_user",
        institution=inst,
        phone="+8801700222888",
        user_type=UserType.STUDENT,
    )
    stu_user.student_profile = student  # type: ignore[attr-defined]
    stu_user.save()
    role_stu, _ = Role.objects.get_or_create(institution=inst, code="student")
    UserRole.objects.get_or_create(user=stu_user, role=role_stu)

    # Fee Heads & Structure
    fh = FeeHead.objects.create(
        institution=inst,
        code="TUITION_C6",
        name_en="Class 6 Tuition",
        name_bn="ক্লাস ৬ বেতন",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    fs = FeeStructure.objects.create(
        institution=inst,
        session=session,
        class_level=class_level,
        name="Class 6 Regular",
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=fs,
        fee_head=fh,
        amount=Decimal("1000.00"),
        due_day=10,
    )

    return {
        "client": client,
        "inst": inst,
        "session": session,
        "class_level": class_level,
        "section": section,
        "admin_user": admin_user,
        "stu_user": stu_user,
        "student": student,
        "fh": fh,
        "fs": fs,
    }


@pytest.mark.django_db
def test_fee_head_and_structure_api(api_fee_setup: dict) -> None:
    client = api_fee_setup["client"]
    admin_user = api_fee_setup["admin_user"]
    stu_user = api_fee_setup["stu_user"]
    fs = api_fee_setup["fs"]

    # Student cannot create fee heads (PermissionDenied)
    client.force_authenticate(user=stu_user)
    res_deny = client.post(
        "/api/v1/fees/heads/",
        {
            "code": "EXAM_FEES",
            "name_en": "Exam Fee",
            "name_bn": "পরীক্ষার ফি",
            "fee_type": "exam",
            "recurrence": "termly",
        },
    )
    assert res_deny.status_code == status.HTTP_403_FORBIDDEN

    # Admin can create fee head
    client.force_authenticate(user=admin_user)
    res_create = client.post(
        "/api/v1/fees/heads/",
        {
            "code": "EXAM_FEES",
            "name_en": "Exam Fee",
            "name_bn": "পরীক্ষার ফি",
            "fee_type": "exam",
            "recurrence": "termly",
        },
    )
    assert res_create.status_code == status.HTTP_201_CREATED
    new_head_id = res_create.data["id"]

    # Admin adds item to fee structure
    res_item = client.post(
        f"/api/v1/fees/structures/{fs.id}/items/",
        {"fee_head": new_head_id, "amount": "500.00", "due_day": 15},
    )
    assert res_item.status_code == status.HTTP_201_CREATED
    assert res_item.data["amount"] == "500.00"


@pytest.mark.django_db
def test_student_waiver_approval_api(api_fee_setup: dict) -> None:
    client = api_fee_setup["client"]
    admin_user = api_fee_setup["admin_user"]
    student = api_fee_setup["student"]
    inst = api_fee_setup["inst"]

    sw = StudentWaiver.objects.create(
        institution=inst,
        student=student,
        title="Merit Waiver",
        discount_type="percentage",
        discount_value=Decimal("25.00"),
        status=WaiverApprovalStatus.PENDING,
    )

    client.force_authenticate(user=admin_user)
    res_app = client.post(f"/api/v1/fees/student-waivers/{sw.id}/approve/")
    assert res_app.status_code == status.HTTP_200_OK
    assert res_app.data["status"] == "approved"
    assert res_app.data["approved_by_name"] == admin_user.username


@pytest.mark.django_db
def test_invoice_generation_bulk_and_pdf_api(api_fee_setup: dict) -> None:
    client = api_fee_setup["client"]
    admin_user = api_fee_setup["admin_user"]
    stu_user = api_fee_setup["stu_user"]
    session = api_fee_setup["session"]
    cls = api_fee_setup["class_level"]
    student = api_fee_setup["student"]

    client.force_authenticate(user=admin_user)

    # 1. Bulk preview
    res_prev = client.post(
        "/api/v1/fees/invoices/bulk-preview/",
        {
            "session_id": str(session.id),
            "class_level_id": str(cls.id),
            "billing_month": 4,
            "billing_year": 2026,
        },
    )
    assert res_prev.status_code == status.HTTP_200_OK
    assert res_prev.data["total_active_students"] == 1
    assert res_prev.data["new_invoices_to_create"] == 1

    # 2. Bulk generate
    res_gen = client.post(
        "/api/v1/fees/invoices/bulk-generate/",
        {
            "session_id": str(session.id),
            "class_level_id": str(cls.id),
            "billing_month": 4,
            "billing_year": 2026,
            "as_issued": True,
        },
    )
    assert res_gen.status_code == status.HTTP_201_CREATED
    assert res_gen.data["created_count"] == 1
    inv_id = res_gen.data["created_invoice_ids"][0]

    # 3. PDF download
    res_pdf = client.get(f"/api/v1/fees/invoices/{inv_id}/pdf/")
    assert res_pdf.status_code == status.HTTP_200_OK
    assert res_pdf["Content-Type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")

    # 4. Due list
    res_due = client.get("/api/v1/fees/due-list/")
    assert res_due.status_code == status.HTTP_200_OK
    assert len(res_due.data) == 1
    assert res_due.data[0]["student_id"] == student.student_id
    assert Decimal(str(res_due.data[0]["total_due_amount"])) == Decimal("1000.00")

    # 5. Student view
    client.force_authenticate(user=stu_user)
    res_stu_list = client.get("/api/v1/fees/invoices/")
    assert res_stu_list.status_code == status.HTTP_200_OK
    assert len(res_stu_list.data["results"]) == 1
    assert res_stu_list.data["results"][0]["id"] == inv_id
