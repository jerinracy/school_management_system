"""Tests for brute force lockout and OTP limits."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserType
from apps.accounts.services.auth import generate_phone_otp
from apps.accounts.test_helpers import make_user
from apps.institutions.models import EducationBoard, Institution, InstitutionType


@pytest.fixture
def institution(db: None) -> Institution:
    return Institution.objects.create(
        name_en="Security Test School",
        name_bn="সিকিউরিটি টেস্ট স্কুল",
        eiin="199888",
        board=EducationBoard.DHAKA,
        type=InstitutionType.SECONDARY,
        division="Dhaka",
        district="Dhaka",
        upazila="Mirpur",
        phone="+8801700000088",
    )


@pytest.fixture
def target_user(db: None, institution: Institution) -> User:
    return make_user(
        username="target_user",
        password="CorrectPassword123!",
        phone="+8801700112233",
        institution=institution,
        user_type=UserType.TEACHER,
    )


@pytest.mark.django_db
class TestBruteForceProtection:
    def test_account_lockout_after_five_failed_attempts(self, target_user: User) -> None:
        client = APIClient()

        # Perform 5 failed attempts
        for _ in range(5):
            res = client.post(
                "/api/v1/auth/login/",
                {"identifier": "target_user", "password": "WrongPassword!"},
                format="json",
            )
            assert res.status_code == status.HTTP_401_UNAUTHORIZED

        # 6th attempt must be locked out with 429
        lockout_res = client.post(
            "/api/v1/auth/login/",
            {"identifier": "target_user", "password": "CorrectPassword123!"},
            format="json",
        )
        assert lockout_res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert lockout_res.data["code"] == "ACCOUNT_LOCKED"


@pytest.mark.django_db
class TestOTPLimits:
    def test_otp_invalidated_after_three_wrong_attempts(self, target_user: User) -> None:
        client = APIClient()
        assert target_user.phone is not None
        generate_phone_otp(target_user.phone, purpose="login")

        # 3 wrong attempts
        for _attempt in range(1, 4):
            res = client.post(
                "/api/v1/auth/otp/verify/",
                {"phone": target_user.phone, "code": "000000", "purpose": "login"},
                format="json",
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST

        # 4th attempt must be rejected because challenge is expired/used
        fourth_res = client.post(
            "/api/v1/auth/otp/verify/",
            {"phone": target_user.phone, "code": "000000", "purpose": "login"},
            format="json",
        )
        assert fourth_res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or expired" in str(fourth_res.data)
