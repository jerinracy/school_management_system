"""Biometric consent, safe enrollment tracking, and device command queueing."""

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.devices.adapters.base import AdapterRegistry
from apps.devices.models import (
    BiometricConsent,
    BiometricEnrollment,
    CommandStatus,
    Device,
    DeviceCommand,
    DeviceUserMap,
)

logger = logging.getLogger(__name__)


def record_biometric_consent(
    institution: Any,
    subject_type: str,
    student: Any = None,
    staff: Any = None,
    guardian: Any = None,
    consent_version: str = "v1.0",
    notes: str = "",
) -> BiometricConsent:
    """Record consent for biometric recognition.

    Enforces AGENTS.md §A3 Rule 4 (child privacy): guardians must sign for students.
    """
    if subject_type == "student":
        if not student:
            raise ValueError("Student reference is required for student consent.")
        if not guardian:
            raise ValueError("Guardian consent is mandatory for school students.")
    elif subject_type == "staff":
        if not staff:
            raise ValueError("Staff reference is required for staff consent.")
    else:
        raise ValueError(f"Unsupported subject_type: {subject_type}")

    return BiometricConsent.objects.create(
        institution=institution,
        subject_type=subject_type,
        student=student,
        staff=staff,
        guardian=guardian,
        consent_version=consent_version,
        notes=notes,
    )


def withdraw_biometric_consent(consent: BiometricConsent) -> BiometricConsent:
    """Withdraw an active biometric consent and decommission device enrollments."""
    with transaction.atomic():
        consent.withdrawn_at = timezone.now()
        consent.save(update_fields=["withdrawn_at", "updated_at"])

        # Deactivate all active enrollments linked to this consent
        enrollments = BiometricEnrollment.objects.filter(
            consent=consent, is_active=True
        ).select_related("device")
        for enrollment in enrollments:
            enrollment.is_active = False
            enrollment.save(update_fields=["is_active", "updated_at"])

            # Queue hardware deletion command
            adapter = AdapterRegistry.get_adapter(enrollment.device)
            delete_payload = adapter.format_delete_command(enrollment.device_user_id)
            queue_device_command(
                device=enrollment.device,
                command_type="delete_user",
                payload=delete_payload,
            )

    return consent


def queue_device_command(
    device: Device,
    command_type: str,
    payload: str = "",
) -> DeviceCommand:
    """Queue an asynchronous command instruction for a hardware terminal."""
    return DeviceCommand.objects.create(
        institution=device.institution,
        device=device,
        command_type=command_type,
        payload=payload,
        status=CommandStatus.QUEUED,
    )


def enroll_user_on_device(
    device: Device,
    user_pin: str,
    user_name: str,
    card_no: str = "",
    student: Any = None,
    staff: Any = None,
    consent: BiometricConsent | None = None,
    method: str | None = None,
) -> tuple[DeviceUserMap, DeviceCommand]:
    """Enroll a user on a terminal with verified consent.

    HARD RULE: Never stores or accepts raw biometric images or templates.
    """
    if not student and not staff:
        raise ValueError("Either student or staff member must be specified.")

    user_type = "student" if student else "staff"

    # Verify active consent exists
    if not consent:
        if student:
            consent = (
                BiometricConsent.objects.filter(student=student, withdrawn_at__isnull=True)
                .order_by("-granted_at")
                .first()
            )
        elif staff:
            consent = (
                BiometricConsent.objects.filter(staff=staff, withdrawn_at__isnull=True)
                .order_by("-granted_at")
                .first()
            )

    if not consent or not consent.is_active:
        raise ValueError("Valid, active biometric consent is required before device enrollment.")

    with transaction.atomic():
        # Update or create DeviceUserMap
        user_map, _ = DeviceUserMap.objects.update_or_create(
            device=device,
            device_user_id=user_pin,
            defaults={
                "institution": device.institution,
                "user_type": user_type,
                "student": student,
                "staff": staff,
                "rfid_card": card_no,
            },
        )

        # Record enrollment metadata
        enrollment_method = method or device.device_type
        BiometricEnrollment.objects.update_or_create(
            institution=device.institution,
            device=device,
            device_user_id=user_pin,
            method=enrollment_method,
            defaults={
                "subject_type": user_type,
                "student": student,
                "staff": staff,
                "consent": consent,
                "is_active": True,
            },
        )

        # Format and queue device command
        adapter = AdapterRegistry.get_adapter(device)
        cmd_payload = adapter.format_enroll_command(user_pin, user_name, card_no)
        cmd = queue_device_command(device, "enroll_user", cmd_payload)

    return user_map, cmd
