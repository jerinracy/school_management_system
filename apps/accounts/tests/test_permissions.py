"""Tests for RBAC, HasModulePermission, and cross-tenant isolation."""

from typing import Any

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.permissions import HasModulePermission
from apps.accounts.test_helpers import api_client_as, make_user
from apps.institutions.models import EducationBoard, Institution, InstitutionType


class DummyGuardedView(APIView):
    permission_classes = [HasModulePermission("test_module_view")]

    def get(self, request: Any) -> Response:
        return Response({"status": "allowed"})


@pytest.fixture
def institution_a(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Institution A",
        name_bn="প্রতিষ্ঠান এ",
        eiin="123001",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Dhanmondi",
        phone="+8801700000010",
    )


@pytest.fixture
def institution_b(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Institution B",
        name_bn="প্রতিষ্ঠান বি",
        eiin="123002",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Gulshan",
        phone="+8801700000020",
    )


@pytest.fixture
def test_permission(db: None) -> Permission:
    ct = ContentType.objects.get_for_model(Role)
    perm, _ = Permission.objects.get_or_create(
        codename="test_module_view",
        content_type=ct,
        defaults={"name": "Can view test module"},
    )
    return perm


@pytest.mark.django_db
class TestModulePermissions:
    def test_user_without_permission_is_denied(self, institution_a: Institution) -> None:
        user = make_user(
            username="unprivileged_user",
            institution=institution_a,
            phone="+8801711111110",
        )
        factory = APIRequestFactory()
        request = factory.get("/")
        force_authenticate(request, user=user)

        view = DummyGuardedView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_role_permission_is_allowed(
        self, institution_a: Institution, test_permission: Permission
    ) -> None:
        user = make_user(
            username="privileged_teacher",
            institution=institution_a,
            phone="+8801711111112",
        )
        role = Role.objects.create(
            institution=institution_a,
            name="Test Role",
            code="test_role",
        )
        role.permissions.add(test_permission)
        UserRole.objects.create(user=user, role=role)

        factory = APIRequestFactory()
        request = factory.get("/")
        force_authenticate(request, user=user)

        view = DummyGuardedView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "allowed"

    def test_superuser_bypasses_permission_check(self) -> None:
        super_user = User.objects.create_superuser(
            username="platform_admin",
            password="AdminPassword123!",
            phone="+8801700000000",
        )
        factory = APIRequestFactory()
        request = factory.get("/")
        force_authenticate(request, user=super_user)

        view = DummyGuardedView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCrossTenantUserIsolation:
    def test_admin_cannot_access_other_tenant_users(
        self, institution_a: Institution, institution_b: Institution
    ) -> None:
        ct = ContentType.objects.get_for_model(User)
        manage_perm, _ = Permission.objects.get_or_create(
            codename="manage_users",
            content_type=ct,
            defaults={"name": "Can manage users"},
        )

        admin_a = make_user(
            username="admin_a",
            institution=institution_a,
            user_type=UserType.ADMIN,
            phone="+8801700000011",
        )
        admin_a.is_staff = True
        admin_a.save()

        role_a = Role.objects.create(institution=institution_a, name="Admin Role", code="admin")
        role_a.permissions.add(manage_perm)
        UserRole.objects.create(user=admin_a, role=role_a)

        user_b = make_user(
            username="student_b",
            institution=institution_b,
            phone="+8801700000022",
        )

        client_a = api_client_as(admin_a)

        # Admin A listing users only sees users of institution A
        list_res = client_a.get("/api/v1/auth/users/")
        assert list_res.status_code == status.HTTP_200_OK
        user_ids = [u["id"] for u in list_res.data["results"]]
        assert str(admin_a.id) in user_ids
        assert str(user_b.id) not in user_ids

        # Admin A retrieving user B directly gets 404
        get_res = client_a.get(f"/api/v1/auth/users/{user_b.id}/")
        assert get_res.status_code == status.HTTP_404_NOT_FOUND
