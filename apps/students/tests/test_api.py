"""API tests for Students app endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.test_helpers import api_client_as, make_user
from apps.admissions.models import AdmissionCircular, Application, ApplicationStatus
from apps.guardians.models import Guardian, StudentGuardian
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment


@pytest.fixture
def student_permissions(db):
    ct = ContentType.objects.get_for_model(Student)
    p_view, _ = Permission.objects.get_or_create(
        codename="view",
        content_type=ct,
        defaults={"name": "Can view students"},
    )
    p_manage, _ = Permission.objects.get_or_create(
        codename="manage",
        content_type=ct,
        defaults={"name": "Can manage students"},
    )
    return p_view, p_manage


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা মডেল স্কুল",
        name_en="Dhaka Model School",
        eiin="134567",
    )


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(
        name_bn="চট্টগ্রাম পাবলিক স্কুল",
        name_en="Chittagong Public School",
        eiin="987654",
    )


@pytest.fixture
def branch(institution) -> Branch:
    return Branch.objects.create(
        institution=institution,
        name="Main Campus",
        code="MAIN",
    )


@pytest.fixture
def shift(branch) -> Shift:
    return Shift.objects.create(
        institution=branch.institution,
        branch=branch,
        name="morning",
        start_time="08:00",
        end_time="12:00",
    )


@pytest.fixture
def session(institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def class_level(institution) -> ClassLevel:
    return ClassLevel.objects.create(
        institution=institution,
        name="Class 10",
        code="CLS10",
        order=10,
    )


@pytest.fixture
def section(class_level, session, shift) -> Section:
    return Section.objects.create(
        institution=class_level.institution,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Section A",
    )


@pytest.fixture
def admin_user(institution, student_permissions) -> User:
    p_view, p_manage = student_permissions
    user = make_user(
        username="admin_user",
        institution=institution,
        user_type=UserType.ADMIN,
        phone="+8801711000001",
    )
    role = Role.objects.create(institution=institution, name="Admin", code="admin")
    role.permissions.add(p_view, p_manage)
    UserRole.objects.create(user=user, role=role)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture
def teacher_user(institution, student_permissions) -> User:
    p_view, _ = student_permissions
    user = make_user(
        username="teacher_user",
        institution=institution,
        user_type=UserType.TEACHER,
        phone="+8801711000002",
    )
    role = Role.objects.create(institution=institution, name="Teacher", code="teacher")
    role.permissions.add(p_view)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def client(admin_user) -> APIClient:
    return api_client_as(admin_user)


@pytest.fixture
def teacher_client(teacher_user) -> APIClient:
    return api_client_as(teacher_user)


@pytest.mark.django_db
class TestStudentAPI:
    def test_student_list_and_search(self, client, institution, session, class_level, section):
        s1 = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Nafis Iqbal",
            name_bn="নাফিস ইকবাল",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
            birth_reg_no="20101234567890123",
        )
        StudentEnrollment.objects.create(
            institution=institution,
            student=s1,
            session=session,
            class_level=class_level,
            section=section,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        # Search by Bangla name
        res = client.get("/api/v1/students/?search=নাফিস")
        assert res.status_code == status.HTTP_200_OK
        results = res.json()["results"]
        assert len(results) == 1
        assert results[0]["student_id"] == "2026100001"

        # Search by ID
        res = client.get("/api/v1/students/?search=2026100001")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.json()["results"]) == 1

    def test_field_level_masking_for_teacher(
        self, teacher_client, institution, session, class_level, section
    ):
        student = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Protected Student",
            name_bn="সুরক্ষিত শিক্ষার্থী",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
            birth_reg_no="20101234567890123",
            emergency_contact_phone="+8801711223344",
        )

        res = teacher_client.get(f"/api/v1/students/{student.id}/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        # Sensitive birth reg no and phone must be masked for non-manage users
        assert data["birth_reg_no"] == "2010*********0123"
        assert "****" in data["emergency_contact_phone"]

    def test_admit_from_application_api(self, client, institution, session, class_level, section):
        circular = AdmissionCircular.objects.create(
            institution=institution,
            session=session,
            class_level=class_level,
            title="Class 10 Admission 2026",
            application_fee=Decimal("0.00"),
            seats_available=50,
            form_open_date=date(2026, 1, 1),
            form_close_date=date(2026, 1, 31),
        )
        application = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00001",
            name_en="Admitted Applicant",
            name_bn="ভর্তিপ্রাপ্ত আবেদনকারী",
            dob=date(2010, 5, 20),
            gender="male",
            birth_reg_no="20101234567890123",
            guardian_name="Guardian Name",
            guardian_phone="+8801711223344",
            status=ApplicationStatus.ADMITTED,
        )

        payload = {
            "application_id": str(application.id),
            "section_id": str(section.id),
            "roll_no": 5,
        }
        res = client.post("/api/v1/students/admit-from-application/", data=payload)
        assert res.status_code == status.HTTP_201_CREATED
        student_data = res.json()["student"]
        assert student_data["student_id"] == "2026100001"

    def test_export_students_excel(self, client, institution):
        Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Exported Student",
            name_bn="রপ্তানি শিক্ষার্থী",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )

        res = client.get("/api/v1/students/export/")
        assert res.status_code == status.HTTP_200_OK
        assert (
            res["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(res.content) > 1000

    def test_student_detail_includes_guardians(self, client, institution):
        student = Student.objects.create(
            institution=institution,
            student_id="2026100099",
            name_en="Tanvir Ahmed",
            name_bn="তানভীর আহমেদ",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )
        guardian = Guardian.objects.create(
            institution=institution,
            name_en="Faruk Ahmed",
            name_bn="ফারুক আহমেদ",
            phone="+8801719988776",
            relation_default="father",
            occupation="Engineer",
        )
        StudentGuardian.objects.create(
            institution=institution,
            student=student,
            guardian=guardian,
            relation="father",
            is_primary=True,
            can_pickup=True,
            receives_sms=True,
            financial_responsible=True,
        )

        res = client.get(f"/api/v1/students/{student.id}/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "guardians" in data
        assert len(data["guardians"]) == 1
        g_info = data["guardians"][0]
        assert g_info["name_en"] == "Faruk Ahmed"
        assert g_info["name_bn"] == "ফারুক আহমেদ"
        assert g_info["phone"] == "+8801719988776"
        assert g_info["relation"] == "father"
        assert g_info["is_primary"] is True
        assert g_info["can_pickup"] is True
        assert g_info["receives_sms"] is True
        assert g_info["financial_responsible"] is True

    def test_id_card_and_transfer_certificate_flow(
        self, client, institution, session, class_level, section
    ):
        student = Student.objects.create(
            institution=institution,
            student_id="2026100001",
            name_en="Cert Student",
            name_bn="সনদ শিক্ষার্থী",
            dob=date(2010, 1, 1),
            gender="female",
            admission_date=date(2026, 1, 1),
        )
        StudentEnrollment.objects.create(
            institution=institution,
            student=student,
            session=session,
            class_level=class_level,
            section=section,
            roll_no=1,
            enrollment_date=date(2026, 1, 1),
            status=EnrollmentStatus.ACTIVE,
        )

        # 1. ID Card PDF
        res = client.get(f"/api/v1/students/{student.id}/id-card/?download=pdf")
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-")

        # 2. Issue TC
        tc_res = client.post(
            "/api/v1/students/transfer-certificates/issue/",
            data={
                "student_id": str(student.id),
                "reason": "Relocating to another city",
            },
        )
        assert tc_res.status_code == status.HTTP_201_CREATED
        tc_id = tc_res.json()["id"]

        # 3. Download TC PDF
        pdf_res = client.get(f"/api/v1/students/transfer-certificates/{tc_id}/download-pdf/")
        assert pdf_res.status_code == status.HTTP_200_OK
        assert pdf_res["Content-Type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF-")

    def test_cross_tenant_isolation(self, client, other_institution, session, class_level, section):
        other_student = Student.objects.create(
            institution=other_institution,
            student_id="OTHER001",
            name_en="Other School Student",
            name_bn="অন্য বিদ্যালয়",
            dob=date(2010, 1, 1),
            gender="male",
            admission_date=date(2026, 1, 1),
        )

        res = client.get(f"/api/v1/students/{other_student.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
