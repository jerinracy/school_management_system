"""Tests for core authentication flows, OTP, profile, and sessions."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import OTPChallenge, User, UserSession, UserType
from apps.accounts.services.auth import generate_phone_otp
from apps.accounts.test_helpers import api_client_as, make_user
from apps.institutions.models import EducationBoard, Institution, InstitutionType


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka High School",
        name_bn="ঢাকা হাই স্কুল",
        eiin="199999",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Dhanmondi",
        phone="+8801700000099",
    )


@pytest.fixture
def test_user(db: None, institution: Institution) -> User:
    return make_user(
        username="teacher_john",
        phone="+8801711223344",
        password="ValidPassword123!",
        institution=institution,
        user_type=UserType.TEACHER,
    )


@pytest.mark.django_db
class TestAuthenticationFlows:
    def test_login_with_username_and_password(self, test_user: User) -> None:
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/",
            {"identifier": "teacher_john", "password": "ValidPassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["username"] == "teacher_john"

        # Verify UserSession is recorded
        assert UserSession.objects.filter(user=test_user).count() == 1

    def test_login_with_phone_number(self, test_user: User) -> None:
        client = APIClient()
        # Login using 01711223344 without country code (should normalize automatically)
        response = client.post(
            "/api/v1/auth/login/",
            {"identifier": "01711223344", "password": "ValidPassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_with_invalid_password(self, test_user: User) -> None:
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/",
            {"identifier": "teacher_john", "password": "WrongPassword!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "AUTHENTICATION_REQUIRED"

    def test_token_refresh(self, test_user: User) -> None:
        client = APIClient()
        login_res = client.post(
            "/api/v1/auth/login/",
            {"identifier": "teacher_john", "password": "ValidPassword123!"},
            format="json",
        )
        refresh_token = login_res.data["refresh"]

        refresh_res = client.post(
            "/api/v1/auth/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert refresh_res.status_code == status.HTTP_200_OK
        assert "access" in refresh_res.data

    def test_logout_revokes_session(self, test_user: User) -> None:
        client = APIClient()
        login_res = client.post(
            "/api/v1/auth/login/",
            {"identifier": "teacher_john", "password": "ValidPassword123!"},
            format="json",
        )
        access_token = login_res.data["access"]
        refresh_token = login_res.data["refresh"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_res = client.post(
            "/api/v1/auth/logout/",
            {"refresh": refresh_token},
            format="json",
        )
        assert logout_res.status_code == status.HTTP_200_OK

        # Session should be revoked
        session = UserSession.objects.filter(user=test_user).first()
        assert session is not None
        assert session.revoked_at is not None

    def test_password_change(self, test_user: User) -> None:
        client = api_client_as(test_user)
        test_user.must_change_password = True
        test_user.save()

        response = client.post(
            "/api/v1/auth/password/change/",
            {
                "old_password": "ValidPassword123!",
                "new_password": "NewSecretPassword2026!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.check_password("NewSecretPassword2026!") is True
        assert test_user.must_change_password is False


@pytest.mark.django_db
class TestOTPFlows:
    def test_request_and_verify_otp(self, test_user: User) -> None:
        client = APIClient()

        # Request OTP
        req_res = client.post(
            "/api/v1/auth/otp/request/",
            {"phone": "01711223344", "purpose": "login"},
            format="json",
        )
        assert req_res.status_code == status.HTTP_200_OK

        challenge = OTPChallenge.objects.filter(phone=test_user.phone).first()
        assert challenge is not None
        assert challenge.is_valid() is True

        # Generate known OTP for verification test
        assert test_user.phone is not None
        code = generate_phone_otp(test_user.phone, purpose="login")

        # Verify OTP
        verify_res = client.post(
            "/api/v1/auth/otp/verify/",
            {"phone": test_user.phone, "code": code, "purpose": "login"},
            format="json",
        )
        assert verify_res.status_code == status.HTTP_200_OK
        assert "access" in verify_res.data
        assert "refresh" in verify_res.data


@pytest.mark.django_db
class TestUserProfile:
    def test_get_current_profile_me(self, test_user: User) -> None:
        client = api_client_as(test_user)
        response = client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == test_user.username
        assert "permissions" in response.data

    def test_update_profile_me(self, test_user: User) -> None:
        client = api_client_as(test_user)
        response = client.patch(
            "/api/v1/auth/me/",
            {"full_name": "John Doe", "language_preference": "en"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.full_name == "John Doe"
        assert test_user.language_preference == "en"
