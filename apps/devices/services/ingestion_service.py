"""Punch ingestion and identity resolution service."""

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.devices.models import (
    Device,
    DeviceStatus,
    DeviceUserMap,
    RawPunch,
    RawPunchStatus,
)

logger = logging.getLogger(__name__)


def ingest_raw_punches(
    device: Device,
    punch_dicts: list[dict[str, Any]],
) -> tuple[int, int, int]:
    """Ingest a batch of normalized punch dicts from a device.

    Returns:
        tuple of (created_count, duplicate_count, unmapped_count)
    """
    if not punch_dicts:
        return 0, 0, 0

    now = timezone.now()
    created_count = 0
    duplicate_count = 0
    unmapped_count = 0

    # Ensure device is marked online and last_seen is updated
    device.last_seen = now
    device.status = DeviceStatus.ONLINE
    device.save(update_fields=["last_seen", "status", "updated_at"])

    # Extract distinct user pins
    user_ids = {str(p["raw_user_id"]).strip() for p in punch_dicts if "raw_user_id" in p}

    # Fetch existing mappings for this device
    mappings = {
        m.device_user_id: m
        for m in DeviceUserMap.objects.filter(
            device=device,
            device_user_id__in=user_ids,
        ).select_related("student", "staff")
    }

    # Extract all timestamps to check for existing punches
    timestamps = [p["device_time"] for p in punch_dicts if "device_time" in p]
    min_time = min(timestamps) if timestamps else now
    max_time = max(timestamps) if timestamps else now

    existing_punches = set(
        RawPunch.objects.filter(
            device=device,
            raw_user_id__in=user_ids,
            device_time__gte=min_time,
            device_time__lte=max_time,
        ).values_list("raw_user_id", "device_time")
    )

    punches_to_create: list[RawPunch] = []

    for punch_data in punch_dicts:
        user_id = str(punch_data.get("raw_user_id", "")).strip()
        dt = punch_data.get("device_time")
        if not user_id or not dt:
            continue

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        # Check for duplicate
        if (user_id, dt) in existing_punches:
            duplicate_count += 1
            continue

        # Calculate clock drift
        drift_seconds = int(abs((now - dt).total_seconds()))

        # Determine mapping and status
        mapping = mappings.get(user_id)
        if mapping and (mapping.student or mapping.staff):
            resolved_student = mapping.student
            resolved_staff = mapping.staff
            status = RawPunchStatus.UNPROCESSED
        else:
            resolved_student = None
            resolved_staff = None
            status = RawPunchStatus.UNMAPPED
            unmapped_count += 1

        payload_hash = punch_data.get("payload_hash", "")
        if not payload_hash:
            import hashlib

            raw_str = f"{user_id}_{dt.isoformat()}_{punch_data.get('punch_state', '0')}"
            payload_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        punch_obj = RawPunch(
            institution=device.institution,
            device=device,
            serial_no=device.serial_no,
            raw_user_id=user_id,
            device_time=dt,
            clock_drift_seconds=drift_seconds,
            verify_type=punch_data.get("verify_type", device.device_type),
            punch_state=str(punch_data.get("punch_state", "0")),
            work_code=str(punch_data.get("work_code", "")),
            payload_hash=payload_hash,
            status=status,
            resolved_student=resolved_student,
            resolved_staff=resolved_staff,
        )
        punches_to_create.append(punch_obj)
        existing_punches.add((user_id, dt))

    if punches_to_create:
        with transaction.atomic():
            created_objs = RawPunch.objects.bulk_create(punches_to_create, ignore_conflicts=True)
            created_count = len(created_objs)

    logger.info(
        "Device %s ingested punches: %d created, %d duplicates, %d unmapped",
        device.name,
        created_count,
        duplicate_count,
        unmapped_count,
    )
    return created_count, duplicate_count, unmapped_count


def resolve_unmapped_punch(
    raw_punch: RawPunch,
    student: Any = None,
    staff: Any = None,
    create_mapping: bool = True,
) -> RawPunch:
    """Resolve an unmapped punch to a student or staff member and optionally create DeviceUserMap."""
    if not student and not staff:
        raise ValueError("Either student or staff member must be specified to resolve punch.")

    with transaction.atomic():
        raw_punch.resolved_student = student
        raw_punch.resolved_staff = staff
        raw_punch.status = RawPunchStatus.UNPROCESSED
        raw_punch.error_message = ""
        raw_punch.save(
            update_fields=[
                "resolved_student",
                "resolved_staff",
                "status",
                "error_message",
                "updated_at",
            ]
        )

        if create_mapping:
            user_type = "student" if student else "staff"
            DeviceUserMap.objects.update_or_create(
                device=raw_punch.device,
                device_user_id=raw_punch.raw_user_id,
                defaults={
                    "institution": raw_punch.device.institution,
                    "user_type": user_type,
                    "student": student,
                    "staff": staff,
                },
            )

            # Re-resolve any other pending unmapped punches for this user on this device
            RawPunch.objects.filter(
                device=raw_punch.device,
                raw_user_id=raw_punch.raw_user_id,
                status=RawPunchStatus.UNMAPPED,
            ).update(
                resolved_student=student,
                resolved_staff=staff,
                status=RawPunchStatus.UNPROCESSED,
                error_message="",
            )

    return raw_punch
