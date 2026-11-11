"""Unit tests for Bangladeshi utility functions."""

from datetime import datetime, timezone

import pytest

from apps.core.utils.bangla import bangla_to_english_digits, english_to_bangla_digits
from apps.core.utils.phone import normalize_bd_phone, validate_bd_phone
from apps.core.utils.timezone import get_dhaka_now, to_dhaka_time


class TestBanglaDigits:
    def test_english_to_bangla_digits(self) -> None:
        assert english_to_bangla_digits("0123456789") == "০১২৩৪৫৬৭৮৯"
        assert english_to_bangla_digits(1971) == "১৯৭১"
        assert english_to_bangla_digits("GPA 5.00") == "GPA ৫.০০"
        assert english_to_bangla_digits("") == ""

    def test_bangla_to_english_digits(self) -> None:
        assert bangla_to_english_digits("০১২৩৪৫৬৭৮৯") == "0123456789"
        assert bangla_to_english_digits("রোল: ০৫") == "রোল: 05"
        assert bangla_to_english_digits("") == ""


class TestBDPhoneUtils:
    @pytest.mark.parametrize(
        "phone",
        [
            "01712345678",
            "01812345678",
            "01912345678",
            "01512345678",
            "01612345678",
            "01312345678",
            "01412345678",
            "+8801712345678",
            "8801712345678",
            "01712-345678",
            "01712 345 678",
        ],
    )
    def test_valid_bd_phone_numbers(self, phone: str) -> None:
        assert validate_bd_phone(phone) is True
        normalized = normalize_bd_phone(phone)
        assert normalized == "+8801712345678" or normalized.startswith("+8801")
        assert len(normalized) == 14

    @pytest.mark.parametrize(
        "phone",
        [
            "01212345678",  # Invalid operator 012
            "01112345678",  # Invalid operator 011 (Citycell retired)
            "029876543",  # Landline
            "123456789",  # Too short
            "+12025550143",  # US number
            "abcdefghijk",  # Non-digits
            "",  # Empty
        ],
    )
    def test_invalid_bd_phone_numbers(self, phone: str) -> None:
        assert validate_bd_phone(phone) is False
        with pytest.raises(ValueError):
            normalize_bd_phone(phone)


class TestDhakaTimezone:
    def test_get_dhaka_now(self) -> None:
        now = get_dhaka_now()
        # Asia/Dhaka is UTC+6
        assert now.tzinfo is not None
        assert now.utcoffset().total_seconds() == 6 * 3600  # type: ignore[union-attr]

    def test_to_dhaka_time(self) -> None:
        utc_dt = datetime(2026, 11, 11, 6, 0, 0, tzinfo=timezone.utc)
        dhaka_dt = to_dhaka_time(utc_dt)
        # 06:00 UTC == 12:00 Dhaka
        assert dhaka_dt.hour == 12
        assert dhaka_dt.day == 11
