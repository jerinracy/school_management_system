"""Authentication services: login, session tokens, OTP, and brute-force protection."""

import logging
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    LoginAttempt,
    OTPChallenge,
    OTPPurpose,
    User,
    UserSession,
)
from apps.core.utils.phone import normalize_bd_phone

from .sms import get_sms_service

logger = logging.getLogger(__name__)

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_MINUTES = 15
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3


def record_login_attempt(
    identifier: str, ip_address: str | None = None, successful: bool = False
) -> None:
    """Record an authentication attempt for rate-limiting and audit."""
    try:
        LoginAttempt.objects.create(
            identifier=identifier.lower().strip(),
            ip_address=ip_address,
            successful=successful,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to record login attempt: %s", exc)


def is_account_locked(identifier: str) -> bool:
    """Check if identifier has failed 5+ consecutive logins in the last 15 minutes."""
    cutoff = timezone.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    recent_attempts = LoginAttempt.objects.filter(
        identifier=identifier.lower().strip(),
        created_at__gte=cutoff,
    ).order_by("-created_at")[:LOCKOUT_THRESHOLD]

    if len(recent_attempts) < LOCKOUT_THRESHOLD:
        return False

    return all(not attempt.successful for attempt in recent_attempts)


def generate_phone_otp(phone: str, purpose: str = OTPPurpose.LOGIN) -> str:
    """Generate and dispatch a 6-digit phone OTP via SMS."""
    normalized_phone = normalize_bd_phone(phone)

    # Rate limiting: max 3 requests per 5 minutes
    recent_requests = OTPChallenge.objects.filter(
        phone=normalized_phone,
        created_at__gte=timezone.now() - timedelta(minutes=5),
    ).count()
    if recent_requests >= 3:
        raise ValidationError(
            "Too many OTP requests. Please wait a few minutes before trying again."
        )

    # Generate 6-digit numeric OTP
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    code_hash = make_password(code)
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    OTPChallenge.objects.create(
        phone=normalized_phone,
        code_hash=code_hash,
        purpose=purpose,
        expires_at=expires_at,
    )

    message = f"Your School Management verification code is {code}. Valid for {OTP_EXPIRY_MINUTES} minutes."
    sms_service = get_sms_service()
    sms_service.send_sms(normalized_phone, message)

    return code


def verify_phone_otp(
    phone: str,
    code: str,
    purpose: str = OTPPurpose.LOGIN,
    institution_id: UUID | str | None = None,
) -> User:
    """Verify submitted OTP code and return matching user."""
    normalized_phone = normalize_bd_phone(phone)

    challenge = (
        OTPChallenge.objects.filter(
            phone=normalized_phone,
            purpose=purpose,
            used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )

    if not challenge or not challenge.is_valid():
        raise ValidationError("Invalid or expired verification code.")

    challenge.attempts += 1
    challenge.save(update_fields=["attempts", "updated_at"])

    if not check_password(code, challenge.code_hash):
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.used_at = timezone.now()
            challenge.save(update_fields=["used_at", "updated_at"])
            raise ValidationError(
                "Maximum verification attempts exceeded. Please request a new code."
            )
        raise ValidationError("Invalid verification code.")

    # Mark as successfully used
    challenge.used_at = timezone.now()
    challenge.save(update_fields=["used_at", "updated_at"])

    # Locate user attached to phone
    user_query = User.objects.filter(phone=normalized_phone, is_active=True)
    if institution_id:
        user_query = user_query.filter(institution_id=institution_id)

    user = user_query.first()
    if not user:
        raise ValidationError("No active user account found associated with this phone number.")

    return user


def issue_tokens_for_user(
    user: User,
    device_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Issue JWT access and refresh tokens and register the active UserSession."""
    refresh = RefreshToken.for_user(user)

    # Incorporate minimal necessary claims in JWT
    refresh["user_id"] = str(user.id)
    refresh["username"] = user.username
    refresh["user_type"] = user.user_type
    refresh["institution_id"] = str(user.institution_id) if user.institution_id else None

    # Role codes
    role_codes = list(user.user_roles.values_list("role__code", flat=True))
    refresh["roles"] = role_codes

    jti = str(refresh.get("jti"))

    # Record UserSession
    info = device_info or {}
    UserSession.objects.create(
        user=user,
        refresh_token_jti=jti,
        device_id=info.get("device_id", ""),
        device_name=info.get("device_name", ""),
        platform=info.get("platform", "web"),
        app_version=info.get("app_version", ""),
        fcm_token=info.get("fcm_token", ""),
        ip_address=info.get("ip_address"),
        user_agent=info.get("user_agent", ""),
    )

    access_token = getattr(refresh, "access_token", refresh)

    return {
        "access": str(access_token),
        "refresh": str(refresh),
        "user": {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "phone": user.phone,
            "email": user.email,
            "user_type": user.user_type,
            "institution_id": str(user.institution_id) if user.institution_id else None,
            "roles": role_codes,
            "must_change_password": user.must_change_password,
            "language_preference": user.language_preference,
        },
    }


def revoke_user_session(session_id: UUID | str, user: User) -> None:
    """Revoke a specific user session."""
    session = UserSession.objects.filter(id=session_id, user=user).first()
    if session and session.is_active:
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])


def revoke_all_user_sessions(user: User) -> None:
    """Revoke all active sessions for a user."""
    UserSession.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now(),
        updated_at=timezone.now(),
    )
