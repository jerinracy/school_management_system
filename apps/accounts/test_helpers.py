"""Test helpers for accounts, users, and API clients."""

from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.institutions.models import Institution


def make_user(
    username: str = "testuser",
    role: str | None = None,
    institution: Institution | None = None,
    user_type: str = UserType.TEACHER,
    permissions: list[str] | None = None,
    phone: str = "+8801700000001",
    password: str = "securepass123",
) -> User:
    """Convenience helper to create a test user with assigned roles and permissions."""
    user = User.objects.create_user(
        username=username,
        password=password,
        phone=phone,
        institution=institution,
        user_type=user_type,
    )

    if role and institution:
        role_obj, _ = Role.objects.get_or_create(
            institution=institution,
            code=role,
            defaults={"name": role.replace("_", " ").title()},
        )
        if permissions:
            for perm_codename in permissions:
                perm = Permission.objects.filter(codename=perm_codename).first()
                if perm:
                    role_obj.permissions.add(perm)

        UserRole.objects.get_or_create(user=user, role=role_obj)

    return user


def api_client_as(user: User) -> APIClient:
    """Return an APIClient pre-authenticated as the given user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client
