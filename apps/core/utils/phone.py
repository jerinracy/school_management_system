"""Bangladeshi phone number validation and normalization."""

import re

# Regex for BD mobile numbers:
# Can be +8801XXXXXXXXX, 8801XXXXXXXXX, or 01XXXXXXXXX
# Valid operators: 013, 014, 015, 016, 017, 018, 019
BD_PHONE_REGEX = re.compile(r"^(?:\+?88)?(01[3-9]\d{8})$")


def validate_bd_phone(phone: str) -> bool:
    """Check if the provided phone number is a valid Bangladeshi mobile number.

    Accepts:
    - 017XXXXXXXX
    - 88017XXXXXXXX
    - +88017XXXXXXXX
    """
    if not phone or not isinstance(phone, str):
        return False
    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    return bool(BD_PHONE_REGEX.match(cleaned))


def normalize_bd_phone(phone: str) -> str:
    """Normalize a Bangladeshi mobile number to the E.164 standard (+8801XXXXXXXXX).

    Raises:
        ValueError: If phone number is invalid or cannot be normalized.
    """
    if not phone or not isinstance(phone, str):
        raise ValueError("Phone number must be a non-empty string.")

    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    match = BD_PHONE_REGEX.match(cleaned)
    if not match:
        raise ValueError(
            f"Invalid Bangladeshi phone number: '{phone}'. Expected 11 digits starting with 01[3-9]."
        )

    # match.group(1) is the 11-digit number starting with 01
    eleven_digits = match.group(1)
    return f"+88{eleven_digits}"
