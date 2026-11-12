"""Field-level encryption and key rotation utilities using MultiFernet (AES-128-CBC + HMAC-SHA256)."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _get_fernet_keys() -> list[bytes]:
    raw_keys = getattr(settings, "FIELD_ENCRYPTION_KEYS", None) or []
    if isinstance(raw_keys, str):
        raw_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    if raw_keys:
        return [k.encode("utf-8") if isinstance(k, str) else k for k in raw_keys]

    if not getattr(settings, "DEBUG", False) and not getattr(settings, "TESTING", False):
        # Allow fallback only if explicitly running tests or debug; prod must configure FIELD_ENCRYPTION_KEYS
        if getattr(settings, "REQUIRE_EXPLICIT_ENCRYPTION_KEYS", False):
            raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS must be configured in production.")

    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return [base64.urlsafe_b64encode(digest)]


def get_multi_fernet() -> MultiFernet:
    """Return a MultiFernet instance ordered newest-key-first for rotation."""
    return MultiFernet([Fernet(k) for k in _get_fernet_keys()])


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return a UTF-8 Fernet token."""
    if not plaintext:
        return ""
    token = get_multi_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet token using any configured key in FIELD_ENCRYPTION_KEYS."""
    if not ciphertext:
        return ""
    try:
        plain = get_multi_fernet().decrypt(ciphertext.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt value with configured encryption keys.") from exc


def rotate_ciphertext(ciphertext: str) -> str:
    """Re-encrypt an older-key token under the primary (first) key in FIELD_ENCRYPTION_KEYS."""
    if not ciphertext:
        return ""
    try:
        rotated = get_multi_fernet().rotate(ciphertext.encode("utf-8"))
        return rotated.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to rotate ciphertext with configured encryption keys.") from exc
