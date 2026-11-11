"""Authorized pickup registration and OTP verification services."""

import hashlib
import logging
import secrets
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.accounts.services.sms import get_sms_service
from apps.core.utils.phone import normalize_bd_phone
from apps.guardians.models import AuthorizedPickup, StudentGuardian
from apps.institutions.models import Institution
from apps.students.models import Student

logger = logging.getLogger(__name__)


def register_pickup_person(
    institution: Institution,
    student: Student,
    name: str,
    relation: str,
    phone: str,
    nid: str = "",
    photo: Any = None,
    notes: str = "",
) -> AuthorizedPickup:
    """Register a new designated pickup person for a student."""
    normalized_phone = normalize_bd_phone(phone)

    pickup = AuthorizedPickup.objects.create(
        institution=institution,
        student=student,
        name=name,
        relation=relation,
        phone=normalized_phone,
        nid=nid,
        photo=photo,
        notes=notes,
        is_active=True,
    )

    # Notify primary guardian if available
    primary_link = (
        StudentGuardian.objects.filter(
            student=student,
            is_primary=True,
        )
        .select_related("guardian")
        .first()
    )
    if primary_link and primary_link.guardian.phone:
        msg = (
            f"Authorized pickup person registered for {student.name_en}: "
            f"{name} ({relation}, {normalized_phone})."
        )
        try:
            get_sms_service().send_sms(primary_link.guardian.phone, msg)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to send pickup notification SMS: %s", exc)

    return pickup


def generate_pickup_verification_otp(pickup: AuthorizedPickup) -> str:
    """Generate and dispatch a 6-digit verification code to the student's primary guardian."""
    otp = f"{secrets.randbelow(900000) + 100000:06d}"
    cache_key = f"pickup_otp_{pickup.id}"
    hashed_otp = hashlib.sha256(otp.encode("utf-8")).hexdigest()

    # Store OTP in cache for 10 minutes (600 seconds)
    cache.set(cache_key, hashed_otp, timeout=600)

    # Deliver OTP to student's primary guardian or pickup person
    primary_link = (
        StudentGuardian.objects.filter(
            student=pickup.student,
            is_primary=True,
        )
        .select_related("guardian")
        .first()
    )
    recipient_phone = primary_link.guardian.phone if primary_link else pickup.phone

    msg = f"OTP to verify pickup authorization for {pickup.name}: {otp}. Valid for 10 minutes."
    try:
        get_sms_service().send_sms(recipient_phone, msg)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to dispatch pickup OTP: %s", exc)

    return otp


def verify_pickup_otp(pickup: AuthorizedPickup, entered_otp: str) -> bool:
    """Validate user-entered OTP against the cached challenge and mark pickup as verified."""
    cache_key = f"pickup_otp_{pickup.id}"
    cached_hash = cache.get(cache_key)

    if not cached_hash:
        return False

    entered_hash = hashlib.sha256(entered_otp.strip().encode("utf-8")).hexdigest()
    if secrets.compare_digest(cached_hash, entered_hash):
        cache.delete(cache_key)
        pickup.otp_verified = True
        pickup.otp_verified_at = timezone.now()
        pickup.save(update_fields=["otp_verified", "otp_verified_at"])
        return True

    return False
