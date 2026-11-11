"""TOTP 2FA generation and verification (RFC 6238)."""

import base64
import hashlib
import hmac
import os
import struct
import time


def generate_totp_secret() -> str:
    """Generate a random base32 TOTP secret string (160-bit key)."""
    random_bytes = os.urandom(20)
    return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")


def get_totp_token(secret: str, intervals_no: int | None = None) -> str:
    """Calculate the 6-digit TOTP token for the current 30-second interval."""
    if intervals_no is None:
        intervals_no = int(time.time()) // 30

    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[19] & 0x0F
    code = (struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code:06d}"


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify code against current interval ± window intervals (to tolerate clock drift)."""
    if not secret or not code or len(code) != 6:
        return False

    current_interval = int(time.time()) // 30
    for i in range(-window, window + 1):
        if get_totp_token(secret, current_interval + i) == code:
            return True
    return False
