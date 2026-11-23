"""Tests for academic CRUD and session filtering."""

from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import User, UserType
from apps.accounts.test_helpers import api_client_as, make_user
from apps.institutions.models import AcademicSession, Branch, Institution, Shift


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model School",
        name_bn="ঢাকা মডেল স্কুল",
        eiin="100201",
    )


@pytest.fixture
def admin_user(institution: Institution) -> User:
    return make_user(
        username="admin_user_acad",
        institution=institution,
        user_type=UserType.ADMIN,
        role="admin",
        permissions=[
            "view_classlevel",
            "change_classlevel",
            "add_classlevel",
            "delete_classlevel",
            "view_section",
            "change_section",
            "add_section",
            "delete_section",
            "view_subject",
            "change_subject",
            "add_subject",
            "delete_subject",
        ],
    )


@pytest.fixture
def api_client(admin_user: User) -> APIClient:
    return api_client_as(admin_user)


@pytest.fixture
def branch(institution: Institution) -> Branch:
    return Branch.objects.create(institution=institution, name="Main", code="MAIN")


@pytest.fixture
def shift(institution: Institution, branch: Branch) -> Shift:
    return Shift.objects.create(
        institution=institution,
        branch=branch,
        name="morning",
        start_time="08:00",
        end_time="13:00",
    )


@pytest.fixture
def active_session(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )


@pytest.fixture
def other_session(institution: Institution) -> AcademicSession:
    return AcademicSession.objects.create(
        institution=institution,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        is_current=False,
    )


@pytest.mark.django_db
class TestAcademicCRUDAndSoftDelete:
    def test_class_level_edit_and_soft_delete(
        self, api_client: APIClient, institution: Institution
    ):
        cl = ClassLevel.objects.create(
            institution=institution,
            name="Class 9",
            code="C09",
            order=9,
        )
        # Edit
        res = api_client.patch(
            f"/api/v1/academics/classes/{cl.id}/", {"name": "Grade 9"}, format="json"
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["name"] == "Grade 9"

        # Soft Delete
        del_res = api_client.delete(f"/api/v1/academics/classes/{cl.id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT
        assert not ClassLevel.objects.filter(id=cl.id).exists()
        assert ClassLevel.all_objects.filter(id=cl.id, is_deleted=True).exists()

    def test_section_edit_and_soft_delete_and_session_filtering(
        self,
        api_client: APIClient,
        institution: Institution,
        branch: Branch,
        shift: Shift,
        active_session: AcademicSession,
        other_session: AcademicSession,
    ):
        cl = ClassLevel.objects.create(
            institution=institution,
            name="Class 8",
            code="C08",
            order=8,
        )
        sec_active = Section.objects.create(
            institution=institution,
            class_level=cl,
            shift=shift,
            session=active_session,
            branch=branch,
            name="Padma",
            capacity=50,
        )
        sec_old = Section.objects.create(
            institution=institution,
            class_level=cl,
            shift=shift,
            session=other_session,
            branch=branch,
            name="Meghna",
            capacity=45,
        )

        # Listing without session query param defaults to active session (sec_active)
        list_res = api_client.get("/api/v1/academics/sections/")
        assert list_res.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in list_res.data["results"]]
        assert str(sec_active.id) in ids
        assert str(sec_old.id) not in ids

        # Querying specifically for other_session returns sec_old
        spec_res = api_client.get(f"/api/v1/academics/sections/?session={other_session.id}")
        assert spec_res.status_code == status.HTTP_200_OK
        spec_ids = [item["id"] for item in spec_res.data["results"]]
        assert str(sec_old.id) in spec_ids

        # Edit Section
        patch_res = api_client.patch(
            f"/api/v1/academics/sections/{sec_active.id}/",
            {"name": "Padma Special", "capacity": 60},
            format="json",
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data["name"] == "Padma Special"
        assert patch_res.data["capacity"] == 60

        # Soft Delete Section
        del_res = api_client.delete(f"/api/v1/academics/sections/{sec_active.id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT
        assert not Section.objects.filter(id=sec_active.id).exists()
        assert Section.all_objects.filter(id=sec_active.id, is_deleted=True).exists()

    def test_subject_edit_and_soft_delete(self, api_client: APIClient, institution: Institution):
        subj = Subject.objects.create(
            institution=institution,
            code="101",
            name_en="Bangla 1st",
            name_bn="বাংলা ১ম",
        )
        # Edit
        edit_res = api_client.patch(
            f"/api/v1/academics/subjects/{subj.id}/",
            {"name_en": "Bangla 1st Paper"},
            format="json",
        )
        assert edit_res.status_code == status.HTTP_200_OK
        assert edit_res.data["name_en"] == "Bangla 1st Paper"

        # Soft Delete
        del_res = api_client.delete(f"/api/v1/academics/subjects/{subj.id}/")
        assert del_res.status_code == status.HTTP_204_NO_CONTENT
        assert not Subject.objects.filter(id=subj.id).exists()
        assert Subject.all_objects.filter(id=subj.id, is_deleted=True).exists()
