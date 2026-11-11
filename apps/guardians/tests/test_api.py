"""API integration tests for Guardian, Family, and Authorized Pickup endpoints."""

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.guardians.models import (
    AuthorizedPickup,
    Guardian,
    StudentGuardian,
)
from apps.guardians.services import generate_pickup_verification_otp, link_student_guardian
from apps.institutions.models import Institution
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model School",
        name_bn="ঢাকা মডেল স্কুল",
        eiin="134567",
    )


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Rajshahi Collegiate School",
        name_bn="রাজশাহী কলেজিয়েট স্কুল",
        eiin="765432",
    )


@pytest.fixture
def guardian_permissions(db):
    ct = ContentType.objects.get_for_model(Guardian)
    p_view, _ = Permission.objects.get_or_create(
        codename="view",
        content_type=ct,
        defaults={"name": "Can view guardians"},
    )
    p_manage, _ = Permission.objects.get_or_create(
        codename="manage",
        content_type=ct,
        defaults={"name": "Can manage guardians"},
    )
    return p_view, p_manage


@pytest.fixture
def student_permissions(db):
    ct = ContentType.objects.get_for_model(Student)
    p_view, _ = Permission.objects.get_or_create(
        codename="view",
        content_type=ct,
        defaults={"name": "Can view students"},
    )
    return p_view


@pytest.fixture
def staff_user(db, institution, guardian_permissions, student_permissions) -> User:
    user = make_user(
        username="staff_admin",
        institution=institution,
        user_type=UserType.STAFF,
        phone="+8801700000001",
    )
    role, _ = Role.objects.get_or_create(institution=institution, code="staff_admin")
    p_g_view, p_g_manage = guardian_permissions
    role.permissions.add(p_g_view, p_g_manage, student_permissions)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="2026100001",
        name_en="Samiul Bashar",
        name_bn="সামিউল বাশার",
        gender="male",
        dob="2013-01-10",
        admission_date="2026-01-01",
    )


@pytest.fixture
def other_student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="2026100002",
        name_en="Nafis Iqbal",
        name_bn="নাফিস ইকবাল",
        gender="male",
        dob="2013-03-12",
        admission_date="2026-01-01",
    )


@pytest.fixture
def client_for():
    def _create(user: User) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _create


@pytest.mark.django_db
class TestGuardianAPI:
    def test_guardian_crud(self, client_for, staff_user, institution):
        client = client_for(staff_user)

        # 1. Create Guardian
        payload = {
            "name_en": "Abul Kashem",
            "name_bn": "আবুল কাশেম",
            "relation_default": "father",
            "phone": "01712345678",
            "nid": "19801234567890123",
            "occupation": "Businessman",
        }
        res = client.post("/api/v1/guardians/guardians/", payload)
        assert res.status_code == status.HTTP_201_CREATED
        guardian_id = res.json()["id"]
        assert res.json()["phone"] == "+8801712345678"

        # 2. List
        list_res = client.get("/api/v1/guardians/guardians/")
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()["results"]) == 1

        # 3. Retrieve
        ret_res = client.get(f"/api/v1/guardians/guardians/{guardian_id}/")
        assert ret_res.status_code == status.HTTP_200_OK
        assert ret_res.json()["name_en"] == "Abul Kashem"

        # 4. Update
        patch_res = client.patch(
            f"/api/v1/guardians/guardians/{guardian_id}/",
            {"occupation": "Senior Businessman"},
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.json()["occupation"] == "Senior Businessman"

    def test_link_and_unlink_student(self, client_for, staff_user, institution, student):
        client = client_for(staff_user)
        guardian = Guardian.objects.create(
            institution=institution,
            name_en="Salma Khatun",
            phone="+8801711222333",
        )

        # Link student
        link_res = client.post(
            f"/api/v1/guardians/guardians/{guardian.id}/link-student/",
            {
                "student_id": str(student.id),
                "relation": "mother",
                "is_primary": True,
                "can_pickup": True,
                "receives_sms": True,
                "financial_responsible": True,
            },
        )
        assert link_res.status_code == status.HTTP_200_OK
        assert link_res.json()["is_primary"] is True
        assert StudentGuardian.objects.filter(student=student, guardian=guardian).exists()

        # Unlink student
        unlink_res = client.post(
            f"/api/v1/guardians/guardians/{guardian.id}/unlink-student/",
            {"student_id": str(student.id)},
        )
        assert unlink_res.status_code == status.HTTP_200_OK
        assert not StudentGuardian.objects.filter(student=student, guardian=guardian).exists()

    def test_create_portal_account(self, client_for, staff_user, institution):
        client = client_for(staff_user)
        guardian = Guardian.objects.create(
            institution=institution,
            name_en="Mahmudul Hasan",
            phone="+8801755443322",
        )

        res = client.post(f"/api/v1/guardians/guardians/{guardian.id}/create-portal-account/")
        assert res.status_code == status.HTTP_200_OK
        assert "user_id" in res.json()

        guardian.refresh_from_db()
        assert guardian.user is not None
        assert guardian.user.phone == "+8801755443322"

    def test_my_children_and_guardian_access_control(
        self, client_for, institution, student, other_student, student_permissions
    ):
        # Create guardian user
        guardian_user = make_user(
            username="guardian_user",
            institution=institution,
            user_type=UserType.GUARDIAN,
            phone="+8801799001122",
        )
        guardian = Guardian.objects.create(
            institution=institution,
            user=guardian_user,
            name_en="Parent User",
            phone="+8801799001122",
        )
        link_student_guardian(
            institution=institution,
            student=student,
            guardian=guardian,
            is_primary=True,
        )

        client = client_for(guardian_user)

        # 1. Access my-children endpoint
        res = client.get("/api/v1/guardians/guardians/my-children/")
        assert res.status_code == status.HTTP_200_OK
        children = res.json()
        assert len(children) == 1
        assert children[0]["name_en"] == "Samiul Bashar"

        # 2. Access student detail endpoint directly
        # Linked student: Allowed
        own_res = client.get(f"/api/v1/students/{student.id}/")
        assert own_res.status_code == status.HTTP_200_OK

        # Unlinked student: Denied (IsGuardianOfStudent denies permission)
        unlinked_res = client.get(f"/api/v1/students/{other_student.id}/")
        assert unlinked_res.status_code == status.HTTP_403_FORBIDDEN

    def test_merge_duplicates_endpoint(self, client_for, staff_user, institution, student):
        client = client_for(staff_user)
        g_primary = Guardian.objects.create(
            institution=institution, name_en="Kashem Primary", phone="+8801710000001"
        )
        g_dup1 = Guardian.objects.create(
            institution=institution, name_en="Kashem Duplicate", phone="+8801710000002"
        )
        link_student_guardian(institution, student, g_dup1)

        payload = {
            "primary_guardian_id": str(g_primary.id),
            "duplicate_guardian_ids": [str(g_dup1.id)],
        }
        res = client.post("/api/v1/guardians/guardians/merge-duplicates/", payload)
        assert res.status_code == status.HTTP_200_OK
        assert StudentGuardian.objects.filter(student=student, guardian=g_primary).exists()
        g_dup1.refresh_from_db()
        assert g_dup1.is_deleted is True

    def test_family_and_pickup_endpoints(self, client_for, staff_user, institution, student):
        client = client_for(staff_user)

        # Family CRUD
        f_res = client.post(
            "/api/v1/guardians/families/",
            {"name": "Rahman Family", "primary_contact_phone": "01788990011"},
        )
        assert f_res.status_code == status.HTTP_201_CREATED
        assert f_res.json()["id"] is not None
        assert f_res.json()["family_code"].startswith("FAM-")

        # Pickup CRUD
        p_res = client.post(
            "/api/v1/guardians/pickups/",
            {
                "student": str(student.id),
                "name": "Mohammad Ali",
                "relation": "Driver",
                "phone": "01777889900",
            },
        )
        assert p_res.status_code == status.HTTP_201_CREATED
        pickup_id = p_res.json()["id"]

        pickup = AuthorizedPickup.objects.get(id=pickup_id)
        otp = generate_pickup_verification_otp(pickup)

        # Verify OTP
        otp_res = client.post(
            f"/api/v1/guardians/pickups/{pickup_id}/verify-otp/",
            {"otp": otp},
        )
        assert otp_res.status_code == status.HTTP_200_OK
        assert otp_res.json()["otp_verified"] is True

    def test_cross_tenant_isolation(self, client_for, staff_user, institution, other_institution):
        # Create guardian in other institution
        other_guardian = Guardian.objects.create(
            institution=other_institution,
            name_en="Other Institution Guardian",
            phone="+8801799887711",
        )

        client = client_for(staff_user)
        # Attempting to retrieve other tenant's guardian returns 404
        res = client.get(f"/api/v1/guardians/guardians/{other_guardian.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
