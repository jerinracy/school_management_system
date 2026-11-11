"""Management command to simulate real-time or historical biometric punches."""

import random
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.devices.adapters.simulator import FakeDeviceAdapter
from apps.devices.models import Device, DeviceProtocol, DeviceType
from apps.devices.services import ingest_raw_punches
from apps.institutions.models import Institution


class Command(BaseCommand):
    help = "Simulate biometric hardware punches for automated testing and demo queues."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--device-sn",
            type=str,
            help="Serial number of terminal. If omitted, uses first active device.",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of simulated punches to generate.",
        )
        parser.add_argument(
            "--punch-state",
            type=str,
            default="0",
            help="Punch state (0=Check-in, 1=Check-out).",
        )
        parser.add_argument(
            "--institution-id",
            type=str,
            help="Institution UUID if device auto-creation is needed.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        sn = options.get("device_sn")
        count = options.get("count", 5)
        punch_state = options.get("punch_state", "0")
        inst_id = options.get("institution_id")

        device = None
        if sn:
            device = Device.objects.filter(serial_no=sn, is_active=True).first()
            if not device:
                raise CommandError(f"Device with serial number '{sn}' not found.")
        else:
            device = Device.objects.filter(is_active=True).first()

        if not device:
            # Look up or require institution
            institution = None
            if inst_id:
                institution = Institution.objects.filter(id=inst_id).first()
            else:
                institution = Institution.objects.first()

            if not institution:
                raise CommandError("No institution found to create a simulated device.")

            device = Device.objects.create(
                institution=institution,
                name="Virtual Simulator Terminal",
                vendor="Simulator",
                model="Sim-v1",
                serial_no="SIM-GATE-001",
                device_type=DeviceType.FINGERPRINT,
                protocol=DeviceProtocol.SIMULATOR,
            )
            self.stdout.write(self.style.SUCCESS(f"Created simulated device: {device.serial_no}"))

        adapter = FakeDeviceAdapter(device)
        now = timezone.now()
        punch_dicts = []

        # Find existing mapped user IDs or generate test IDs
        mapped_pins = list(device.user_mappings.values_list("device_user_id", flat=True))
        if not mapped_pins:
            mapped_pins = ["101", "102", "103"]

        for i in range(count):
            # Mix mapped and unmapped user IDs
            if i % 3 == 2:
                user_id = f"UNMAPPED_{random.randint(9000, 9999)}"
            else:
                user_id = random.choice(mapped_pins)

            punch_time = now - timedelta(minutes=i * 2)
            punch_dicts.append(
                {
                    "raw_user_id": user_id,
                    "device_time": punch_time,
                    "verify_type": device.device_type,
                    "punch_state": punch_state,
                    "work_code": "0",
                    "payload_hash": adapter.compute_payload_hash(f"{user_id}:{punch_time}"),
                    "raw_line": f"SIM {user_id} {punch_time}",
                }
            )

        created, duplicates, unmapped = ingest_raw_punches(device, punch_dicts)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully simulated punches on {device.name} ({device.serial_no}): "
                f"{created} created, {duplicates} duplicates, {unmapped} unmapped."
            )
        )
