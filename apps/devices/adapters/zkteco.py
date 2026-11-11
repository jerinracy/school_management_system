"""ZKTeco ADMS (Push SDK / iClock) protocol adapter implementation."""

import logging
from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.devices.adapters.base import AdapterRegistry, BaseDeviceAdapter
from apps.devices.models import DeviceType

logger = logging.getLogger(__name__)


@AdapterRegistry.register("zkteco", "push_adms")
class ZKTecoPushAdapter(BaseDeviceAdapter):
    """Adapter handling ZKTeco ADMS (Automatic Data Master Server) push protocol.

    Verified behavior:
    - HTTP POST to /iclock/cdata?SN={serial}&table=ATTLOG
    - Body lines formatted as tab-separated values:
      {PIN}\t{YYYY-MM-DD HH:MM:SS}\t{STATUS}\t{VERIFY}\t{WORKCODE}
    - Server responds with 'OK: {COUNT}' or 'OK' on success.
    """

    VERIFY_TYPE_MAP = {
        "1": DeviceType.FINGERPRINT,
        "2": DeviceType.PIN,
        "4": DeviceType.RFID,
        "15": DeviceType.FACE,
        "20": DeviceType.PALM,
    }

    def authenticate_request(self, request: Any) -> bool:
        """Validate device serial number and optional token matching."""
        sn = request.GET.get("SN") or request.POST.get("SN")
        if not sn:
            return False
        if sn.strip() != self.device.serial_no.strip():
            return False

        # If device has an api_token configured, verify request token
        if self.device.api_token:
            token = (
                request.headers.get("X-Device-Token")
                or request.GET.get("token")
                or request.GET.get("push_token")
            )
            if token != self.device.api_token:
                return False

        return True

    def parse_push_payload(
        self,
        payload: Any,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Parse raw ATTLOG body string into normalized punch dicts."""
        if isinstance(payload, bytes):
            payload_str = payload.decode("utf-8", errors="replace")
        else:
            payload_str = str(payload)

        punches: list[dict[str, Any]] = []
        lines = payload_str.strip().splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                # Fallback to whitespace split if not tab-separated
                parts = line.split()

            if len(parts) < 2:
                continue

            raw_user_id = parts[0].strip()
            raw_time_str = parts[1].strip()
            punch_state = parts[2].strip() if len(parts) > 2 else "0"
            raw_verify = parts[3].strip() if len(parts) > 3 else "1"
            work_code = parts[4].strip() if len(parts) > 4 else ""

            # Parse datetime: e.g. "2026-03-01 08:15:30"
            dt = parse_datetime(raw_time_str)
            if not dt:
                try:
                    dt = datetime.strptime(raw_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning("Could not parse timestamp in ZKTeco punch: %s", raw_time_str)
                    continue

            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())

            verify_type = self.VERIFY_TYPE_MAP.get(raw_verify, self.device.device_type)
            payload_hash = self.compute_payload_hash(line)

            punches.append(
                {
                    "raw_user_id": raw_user_id,
                    "device_time": dt,
                    "verify_type": verify_type,
                    "punch_state": punch_state,
                    "work_code": work_code,
                    "payload_hash": payload_hash,
                    "raw_line": line,
                }
            )

        return punches

    def format_enroll_command(self, user_pin: str, user_name: str, card_no: str = "") -> str:
        """Format ZKTeco DATA USER command."""
        card_part = f"\tCard={card_no}" if card_no else ""
        return f"DATA USER PIN={user_pin}\tName={user_name}{card_part}\tPri=0"

    def format_delete_command(self, user_pin: str) -> str:
        """Format ZKTeco DATA DELETE USER command."""
        return f"DATA DELETE USER PIN={user_pin}"
