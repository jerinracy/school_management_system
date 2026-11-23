"""Tests for Academic Session lifecycle, activation, and soft delete."""

from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.institutions.models import AcademicSession, Institution, SessionStatus


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model School",
        name_bn="ঢাকা মডেল স্কুল",
        eiin="100201",
    )


@pytest.fixture
def admin_user(db: None, institution: Institution):
    from apps.accounts.models import User

    return User.objects.create_user(
        username="admin_user_sess",
        phone="+8801711000001",
        email="admin@school.edu.bd",
        password="AdminPassword123!",
        user_type="admin",
        is_staff=True,
        institution=institution,
    )


@pytest.fixture
def api_client(admin_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.mark.django_db
class TestAcademicSessionLifecycle:
    def test_create_academic_session(self, api_client: APIClient, institution: Institution):
        payload = {
            "name": "2027 Academic Year",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
        }
        res = api_client.post("/api/v1/institutions/sessions/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name"] == "2027 Academic Year"
        assert res.data["is_current"] is False

    def test_edit_academic_session(self, api_client: APIClient, institution: Institution):
        sess = AcademicSession.objects.create(
            institution=institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        res = api_client.patch(
            f"/api/v1/institutions/sessions/{sess.id}/",
            {"name": "2026 Academic Session Updated"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["name"] == "2026 Academic Session Updated"
        sess.refresh_from_db()
        assert sess.name == "2026 Academic Session Updated"

    def test_activate_session_ensures_single_active_session(
        self, api_client: APIClient, institution: Institution
    ):
        sess1 = AcademicSession.objects.create(
            institution=institution,
            name="2025",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )
        sess2 = AcademicSession.objects.create(
            institution=institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=False,
            status=SessionStatus.PLANNED,
        )

        res = api_client.post(f"/api/v1/institutions/sessions/{sess2.id}/activate/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["is_current"] is True

        sess1.refresh_from_db()
        sess2.refresh_from_db()
        assert sess1.is_current is False
        assert sess2.is_current is True
        assert AcademicSession.objects.filter(institution=institution, is_current=True).count() == 1

    def test_soft_delete_academic_session(self, api_client: APIClient, institution: Institution):
        # Active session cannot be deleted
        active_sess = AcademicSession.objects.create(
            institution=institution,
            name="Active 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
            status=SessionStatus.ACTIVE,
        )
        del_res = api_client.delete(f"/api/v1/institutions/sessions/{active_sess.id}/")
        assert del_res.status_code == status.HTTP_400_BAD_REQUEST

        # Inactive session can be soft-deleted
        inactive_sess = AcademicSession.objects.create(
            institution=institution,
            name="Draft 2028",
            start_date=date(2028, 1, 1),
            end_date=date(2028, 12, 31),
            is_current=False,
            status=SessionStatus.PLANNED,
        )
        del_res2 = api_client.delete(f"/api/v1/institutions/sessions/{inactive_sess.id}/")
        assert del_res2.status_code == status.HTTP_204_NO_CONTENT

        # Excluded from active objects, but preserved in all_objects
        assert not AcademicSession.objects.filter(id=inactive_sess.id).exists()
        assert AcademicSession.all_objects.filter(id=inactive_sess.id, is_deleted=True).exists()
