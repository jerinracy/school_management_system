"""Adapter stubs for vendor hardware protocols requiring on-premise SDKs or hardware bridges.

Documented status:
- Hikvision ISAPI: Protocol specification stubbed; requires HTTP Digest authentication and XML/JSON event notification format.
- Suprema BioStar: Protocol specification stubbed; requires BioStar 2 REST API or device-side G-SDK socket connection.
- eSSL Pull SDK: Protocol specification stubbed; requires Windows/Linux standalone C/Python SDK socket wrapper.
"""

from typing import Any

from apps.devices.adapters.base import AdapterRegistry, BaseDeviceAdapter


@AdapterRegistry.register("hikvision", "generic_http")
class HikvisionISAPIAdapter(BaseDeviceAdapter):
    """Stub for Hikvision ISAPI / Event Notification push protocol.

    Assumed behavior:
    - Hikvision terminals push multipart/form-data or XML/JSON event notifications
      to a configured HTTP listening endpoint.
    - Status: STUB (requires physical terminal or ISAPI emulator for E2E verification).
    """

    def authenticate_request(self, request: Any) -> bool:
        # TODO: Implement HTTP Digest authentication or basic token check
        return True

    def parse_push_payload(
        self, payload: Any, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        # TODO: Parse Hikvision XML EventNotificationAlert or JSON AccessControllerEvent
        return []


@AdapterRegistry.register("suprema", "generic_http")
class SupremaBioStarAdapter(BaseDeviceAdapter):
    """Stub for Suprema BioStar 2 Cloud / Device API.

    Assumed behavior:
    - Suprema terminals communicate via BioStar 2 webhook or G-SDK socket client.
    - Status: STUB (requires BioStar server or hardware for validation).
    """

    def authenticate_request(self, request: Any) -> bool:
        return True

    def parse_push_payload(
        self, payload: Any, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        # TODO: Parse BioStar EventLog structure
        return []


@AdapterRegistry.register("essl", "pull_sdk")
class EsslPullAdapter(BaseDeviceAdapter):
    """Stub for eSSL standalone attendance terminals using socket pull.

    Assumed behavior:
    - Connects directly to terminal IP on port 4370 using pyzk / zklib socket protocol.
    - Status: STUB (requires local network connectivity to device port 4370).
    """

    def authenticate_request(self, request: Any) -> bool:
        return True

    def parse_push_payload(
        self, payload: Any, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return []
