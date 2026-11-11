"""API tests for public admission portal and admin management."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.academics.models import ClassLevel
from apps.accounts.models import User, UserType
from apps.accounts.test_helpers import api_client_as, make_user
from apps.admissions.models import (
    AdmissionCircular,
    Application,
    ApplicationStatus,
    CircularStatus,
    GenderChoices,
)
from apps.institutions.models import AcademicSession, Institution


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_bn="ঢাকা মডেল কলেজ", name_en="Dhaka Model College", eiin="134567"
    )


@pytest.fixture
def other_institution(db: None) -> Institution:
    return Institution.objects.create(
        name_bn="রাজশাহী স্কুল", name_en="Rajshahi School", eiin="987654"
    )


@pytest.fixture
def admin_user(institution: Institution) -> User:
    return make_user(
        username="admission_admin",
        institution=institution,
        user_type=UserType.ADMIN,
        role="admin",
        permissions=[
            "view_admissioncircular",
            "change_admissioncircular",
            "add_admissioncircular",
            "delete_admissioncircular",
            "view_application",
            "change_application",
            "add_application",
            "delete_application",
            "view_quotarule",
            "change_quotarule",
            "view_admissiontest",
            "change_admissiontest",
            "view_admissiontestresult",
            "change_admissiontestresult",
            "view_lotterydraw",
            "view_meritlist",
        ],
    )


@pytest.fixture
def session(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def class_level(institution: Institution) -> ClassLevel:
    return ClassLevel.objects.create(institution=institution, name="Class 6", code="c06", order=6)


@pytest.fixture
def circular(
    institution: Institution, session: AcademicSession, class_level: ClassLevel
) -> AdmissionCircular:
    return AdmissionCircular.objects.create(
        institution=institution,
        session=session,
        class_level=class_level,
        title="Admission 2026 - Class 6",
        seats_available=60,
        application_fee=Decimal("200.00"),
        form_open_date=date(2025, 1, 1),
        form_close_date=date(2027, 12, 31),
        status=CircularStatus.PUBLISHED,
    )


@pytest.mark.django_db
class TestPublicAdmissionsAPI:
    def test_public_circular_list(self, circular: AdmissionCircular) -> None:
        from rest_framework.test import APIClient

        client = APIClient()
        res = client.get("/api/v1/admissions/public/circulars/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]["title"] == circular.title

    def test_public_application_apply_and_track(self, circular: AdmissionCircular) -> None:
        from rest_framework.test import APIClient

        client = APIClient()
        payload = {
            "circular_id": str(circular.id),
            "name_bn": "সাকিব আল হাসান",
            "name_en": "Shakib Al Hasan",
            "dob": "2014-03-24",
            "gender": "male",
            "birth_reg_no": "20141234567890123",
            "guardian_name": "Mashrafe",
            "guardian_phone": "01711223344",
            "guardian_relation": "Father",
            "present_address": "Mirpur, Dhaka",
            "permanent_address": "Magura",
            "previous_school": "Magura Primary School",
            "previous_gpa": "4.50",
            "quota_type": "general",
        }
        res = client.post("/api/v1/admissions/public/apply/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        app_no = res.data["application_no"]
        assert app_no.startswith("ADM-2026-")
        assert res.data["guardian_phone"] == "+8801711223344"

        # Track application
        track_payload = {
            "application_no": app_no,
            "guardian_phone": "01711223344",
        }
        res_track = client.post("/api/v1/admissions/public/track/", track_payload, format="json")
        assert res_track.status_code == status.HTTP_200_OK
        assert res_track.data["application_no"] == app_no


@pytest.mark.django_db
class TestAdminAdmissionsAPI:
    def test_circular_publish_and_close(
        self,
        institution: Institution,
        session: AcademicSession,
        class_level: ClassLevel,
        admin_user: User,
    ) -> None:
        client = api_client_as(admin_user)
        draft_circular = AdmissionCircular.objects.create(
            institution=institution,
            session=session,
            class_level=class_level,
            title="Draft Circular",
            form_open_date=date(2025, 1, 1),
            form_close_date=date(2027, 12, 31),
            status=CircularStatus.DRAFT,
        )
        # Publish
        res_pub = client.post(f"/api/v1/admissions/circulars/{draft_circular.id}/publish/")
        assert res_pub.status_code == status.HTTP_200_OK
        assert res_pub.data["status"] == CircularStatus.PUBLISHED

        # Close
        res_close = client.post(f"/api/v1/admissions/circulars/{draft_circular.id}/close/")
        assert res_close.status_code == status.HTTP_200_OK
        assert res_close.data["status"] == CircularStatus.CLOSED

    def test_application_transition(
        self, circular: AdmissionCircular, admin_user: User, institution: Institution
    ) -> None:
        app = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00055",
            name_bn="নাম",
            name_en="Name",
            dob=date(2014, 1, 1),
            gender=GenderChoices.FEMALE,
            birth_reg_no="20140000000000055",
            guardian_name="Guardian",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.SUBMITTED,
        )
        client = api_client_as(admin_user)
        payload = {
            "new_status": ApplicationStatus.PAID,
            "notes": "Paid at cash counter",
        }
        res = client.post(
            f"/api/v1/admissions/applications/{app.id}/transition/", payload, format="json"
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == ApplicationStatus.PAID

    def test_convert_to_student_stub(
        self, circular: AdmissionCircular, admin_user: User, institution: Institution
    ) -> None:
        app = Application.objects.create(
            institution=institution,
            circular=circular,
            application_no="ADM-2026-00077",
            name_bn="আদৃত শিক্ষার্থী",
            name_en="Admitted Student",
            dob=date(2014, 1, 1),
            gender=GenderChoices.MALE,
            birth_reg_no="20140000000000077",
            guardian_name="Guardian",
            guardian_phone="+8801711000001",
            present_address="Dhaka",
            permanent_address="Dhaka",
            status=ApplicationStatus.ADMITTED,
        )
        client = api_client_as(admin_user)
        res = client.post(f"/api/v1/admissions/applications/{app.id}/convert-to-student/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "pending_student_intake"

    def test_tenant_isolation(
        self, circular: AdmissionCircular, other_institution: Institution, admin_user: User
    ) -> None:
        # Create circular in other institution
        other_session = AcademicSession.objects.create(
            institution=other_institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        other_cls = ClassLevel.objects.create(
            institution=other_institution,
            name="Other Class",
            code="oth01",
            order=1,
        )
        other_circular = AdmissionCircular.objects.create(
            institution=other_institution,
            session=other_session,
            class_level=other_cls,
            title="Other School Circular",
            form_open_date=date(2025, 1, 1),
            form_close_date=date(2027, 12, 31),
        )

        client = api_client_as(admin_user)
        res = client.get(f"/api/v1/admissions/circulars/{other_circular.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
