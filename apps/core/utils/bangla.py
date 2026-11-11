"""Bangla numerals conversion utilities."""

ENGLISH_DIGITS = "0123456789"
BANGLA_DIGITS = "০১২৩৪৫৬৭৮৯"

EN_TO_BN_TRANS = str.maketrans(ENGLISH_DIGITS, BANGLA_DIGITS)
BN_TO_EN_TRANS = str.maketrans(BANGLA_DIGITS, ENGLISH_DIGITS)


def english_to_bangla_digits(value: str | int | float) -> str:
    """Convert English/Arabic numbers (0-9) to Bangla numerals (০-৯).

    Example:
        english_to_bangla_digits(12345) -> "১২৩৪৫"
        english_to_bangla_digits("Roll: 05") -> "Roll: ০৫"
    """
    if value is None:
        return ""
    return str(value).translate(EN_TO_BN_TRANS)


def bangla_to_english_digits(value: str) -> str:
    """Convert Bangla numerals (০-৯) to English/Arabic numbers (0-9).

    Example:
        bangla_to_english_digits("১২৩৪৫") -> "12345"
        bangla_to_english_digits("রোল: ০৫") -> "রোল: 05"
    """
    if not value or not isinstance(value, str):
        return ""
    return value.translate(BN_TO_EN_TRANS)
