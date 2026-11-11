"""Vendor-agnostic hardware adapter interfaces and adapter registry."""

import abc
import hashlib
from typing import Any

from apps.devices.models import Device


class BaseDeviceAdapter(abc.ABC):
    """Abstract base adapter for all biometric hardware integrations."""

    def __init__(self, device: Device):
        self.device = device

    @abc.abstractmethod
    def authenticate_request(self, request: Any) -> bool:
        """Validate whether the incoming HTTP push/webhook request is authorized."""
        pass

    @abc.abstractmethod
    def parse_push_payload(
        self,
        payload: Any,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Parse raw device push bytes/string/JSON into normalized punch dictionaries.

        Expected output item format:
        {
            "raw_user_id": str,
            "device_time": datetime,
            "verify_type": str,
            "punch_state": str,
            "work_code": str,
            "payload_hash": str,
            "raw_line": str,
        }
        """
        pass

    def compute_payload_hash(self, content: str) -> str:
        """Generate SHA-256 fingerprint for immutable punch deduplication."""
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    def format_enroll_command(self, user_pin: str, user_name: str, card_no: str = "") -> str:
        """Format an enrollment command instruction for this hardware protocol."""
        return f"ENROLL PIN={user_pin}\tNAME={user_name}\tCARD={card_no}"

    def format_delete_command(self, user_pin: str) -> str:
        """Format a delete user instruction for this hardware protocol."""
        return f"DELETE PIN={user_pin}"


class AdapterRegistry:
    """Registry resolving adapter implementations based on device vendor and communication protocol."""

    _registry: dict[tuple[str, str], type[BaseDeviceAdapter]] = {}

    @classmethod
    def register(cls, vendor: str, protocol: str) -> Any:
        def decorator(adapter_cls: type[BaseDeviceAdapter]) -> type[BaseDeviceAdapter]:
            cls._registry[(vendor.lower(), protocol.lower())] = adapter_cls
            return adapter_cls

        return decorator

    @classmethod
    def get_adapter(cls, device: Device) -> BaseDeviceAdapter:
        key = (device.vendor.lower(), device.protocol.lower())
        adapter_cls = cls._registry.get(key)
        if not adapter_cls:
            # Fallback to protocol only
            for (_v, p), candidate_cls in cls._registry.items():
                if p == device.protocol.lower():
                    return candidate_cls(device)
            # Default to generic HTTP adapter
            from .generic_http import GenericHTTPAdapter

            return GenericHTTPAdapter(device)
        return adapter_cls(device)
