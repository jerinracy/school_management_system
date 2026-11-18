"""API and permission integration tests for institutions module."""

from datetime import date
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.institutions.models import (
    AcademicSession,
    Branch,
    EducationBoard,
    Institution,
    InstitutionType,
    SessionStatus,
    ShiftName,
)

User = get_user_model()


@pytest.fixture
def institution_a(db: None) -> Institution:
    return Institution.objects.create(
        name_en="School A",
        name_bn="স্কুল এ",
        eiin="111111",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Dhanmondi",
        phone="+8801700000001",
    )


@pytest.fixture
def institution_b(db: None) -> Institution:
    return Institution.objects.create(
        name_en="School B",
        name_bn="স্কুল বি",
        eiin="222222",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Gulshan",
        phone="+8801700000002",
    )


@pytest.fixture
def admin_user_a(db: None, institution_a: Institution) -> Any:
    user: Any = User.objects.create_user(username="admin_a", password="password123")
    user.is_staff = True
    user.institution = institution_a
    user.institution_id = institution_a.id
    user.save()
    return user


@pytest.fixture
def teacher_user_a(db: None, institution_a: Institution) -> Any:
    user: Any = User.objects.create_user(username="teacher_a", password="password123")
    user.is_staff = False
    user.institution = institution_a
    user.institution_id = institution_a.id
    user.user_type = "teacher"
    user.save()
    return user


@pytest.fixture
def admin_user_b(db: None, institution_b: Institution) -> Any:
    user: Any = User.objects.create_user(username="admin_b", password="password123")
    user.is_staff = True
    user.institution = institution_b
    user.institution_id = institution_b.id
    user.save()
    return user


@pytest.mark.django_db
class TestInstitutionPublicBrandingAPI:
    def test_get_public_branding_unauthenticated(self, institution_a: Institution) -> None:
        client = APIClient()
        response = client.get("/api/v1/institutions/public-branding/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name_en"] == "School A"
        assert response.data["name_bn"] == "স্কুল এ"
        assert response.data["eiin"] == "111111"

    def test_get_public_branding_by_eiin(
        self, institution_a: Institution, institution_b: Institution
    ) -> None:
        client = APIClient()
        response = client.get(f"/api/v1/institutions/public-branding/?eiin={institution_b.eiin}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name_en"] == "School B"

    def test_get_public_branding_empty_db_fallback(self) -> None:
        Institution.objects.all().delete()
        client = APIClient()
        response = client.get("/api/v1/institutions/public-branding/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name_en"] == "School Management System"
        assert response.data["name_bn"] == "বিদ্যালয় ব্যবস্থাপনা পদ্ধতি"


@pytest.mark.django_db
class TestInstitutionProfileAPI:
    def test_get_institution_profile(self, admin_user_a: Any, institution_a: Institution) -> None:
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        response = client.get("/api/v1/institutions/profile/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name_en"] == "School A"
        assert response.data["eiin"] == "111111"

    def test_patch_institution_profile_admin(self, admin_user_a: Any) -> None:
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        payload = {"phone": "+8801799999999", "settings": {"bangla_digits": False}}
        response = client.patch("/api/v1/institutions/profile/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == "+8801799999999"
        assert response.data["settings"]["bangla_digits"] is False

    def test_patch_profile_read_only_user_denied(self, teacher_user_a: Any) -> None:
        client = APIClient()
        client.force_authenticate(user=teacher_user_a)

        response = client.patch(
            "/api/v1/institutions/profile/", {"phone": "+8801700000000"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestBranchAndShiftAPI:
    def test_crud_branch(self, admin_user_a: Any, institution_a: Institution) -> None:
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        # Create
        create_res = client.post(
            "/api/v1/institutions/branches/",
            {"name": "Dhanmondi Campus", "code": "DHAN", "is_main": True},
            format="json",
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        branch_id = create_res.data["id"]

        # List
        list_res = client.get("/api/v1/institutions/branches/")
        assert list_res.status_code == status.HTTP_200_OK
        assert list_res.data["count"] == 1
        assert list_res.data["results"][0]["code"] == "DHAN"

        # Update
        patch_res = client.patch(
            f"/api/v1/institutions/branches/{branch_id}/",
            {"name": "Main Dhanmondi Campus"},
            format="json",
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data["name"] == "Main Dhanmondi Campus"

    def test_shift_crud(self, admin_user_a: Any, institution_a: Institution) -> None:
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        branch = Branch.objects.create(institution=institution_a, name="Campus", code="CMP")

        create_res = client.post(
            "/api/v1/institutions/shifts/",
            {
                "branch": str(branch.id),
                "name": ShiftName.MORNING,
                "start_time": "07:30:00",
                "end_time": "12:00:00",
            },
            format="json",
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        assert create_res.data["name"] == ShiftName.MORNING


@pytest.mark.django_db
class TestAcademicSessionLifecycleAPI:
    def test_activate_session_endpoint(self, admin_user_a: Any, institution_a: Institution) -> None:
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        session = AcademicSession.objects.create(
            institution=institution_a,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=False,
            status=SessionStatus.PLANNED,
        )

        response = client.post(f"/api/v1/institutions/sessions/{session.id}/activate/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_current"] is True
        assert response.data["status"] == SessionStatus.ACTIVE

    def test_close_session_endpoint(self, admin_user_a: Any, institution_a: Institution) -> None:
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        session = AcademicSession.objects.create(
            institution=institution_a,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )

        # Attempting without confirm=True must fail
        fail_res = client.post(
            f"/api/v1/institutions/sessions/{session.id}/close/",
            {"confirm": False},
            format="json",
        )
        assert fail_res.status_code == status.HTTP_400_BAD_REQUEST

        # With confirm=True succeeds
        success_res = client.post(
            f"/api/v1/institutions/sessions/{session.id}/close/",
            {"confirm": True},
            format="json",
        )
        assert success_res.status_code == status.HTTP_200_OK
        assert success_res.data["status"] == SessionStatus.CLOSED
        assert success_res.data["is_current"] is False


@pytest.mark.django_db
class TestCrossTenantIsolation:
    def test_cross_tenant_branch_isolation(
        self,
        admin_user_a: Any,
        admin_user_b: Any,
        institution_a: Institution,
        institution_b: Institution,
    ) -> None:
        branch_a = Branch.objects.create(
            institution=institution_a,
            name="Campus A",
            code="CMPA",
        )
        branch_b = Branch.objects.create(
            institution=institution_b,
            name="Campus B",
            code="CMPB",
        )

        client_a = APIClient()
        client_a.force_authenticate(user=admin_user_a)

        # User A listing branches sees only Campus A
        list_res = client_a.get("/api/v1/institutions/branches/")
        assert list_res.status_code == status.HTTP_200_OK
        assert list_res.data["count"] == 1
        assert list_res.data["results"][0]["id"] == str(branch_a.id)

        # User A trying to access Branch B directly gets 404
        retrieve_res = client_a.get(f"/api/v1/institutions/branches/{branch_b.id}/")
        assert retrieve_res.status_code == status.HTTP_404_NOT_FOUND

        # User A trying to delete Branch B gets 404
        delete_res = client_a.delete(f"/api/v1/institutions/branches/{branch_b.id}/")
        assert delete_res.status_code == status.HTTP_404_NOT_FOUND

    def test_create_shift_auto_branch_and_term_auto_order(
        self,
        admin_user_a: Any,
        institution_a: Institution,
    ) -> None:
        branch = Branch.objects.create(
            institution=institution_a,
            name="Main Campus",
            code="MAIN",
        )
        session = AcademicSession.objects.create(
            institution=institution_a,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin_user_a)

        # Create shift without explicitly passing branch
        res_shift = client.post(
            "/api/v1/institutions/shifts/",
            {"name": "Morning Shift", "start_time": "07:30:00", "end_time": "12:00:00"},
            format="json",
        )
        assert res_shift.status_code == status.HTTP_201_CREATED
        assert str(res_shift.data["branch"]) == str(branch.id)

        # Create term without passing order
        res_term = client.post(
            "/api/v1/institutions/terms/",
            {
                "session": str(session.id),
                "name": "1st Mid Term",
                "start_date": "2026-01-15",
                "end_date": "2026-03-31",
            },
            format="json",
        )
        assert res_term.status_code == status.HTTP_201_CREATED
        assert res_term.data["order"] == 1
