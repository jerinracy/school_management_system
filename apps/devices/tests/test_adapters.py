"""Unit tests for hardware device protocol adapters and adapter registry."""

import hashlib
import hmac
from unittest.mock import MagicMock

import pytest

from apps.devices.adapters.base import AdapterRegistry
from apps.devices.adapters.generic_http import GenericHTTPAdapter
from apps.devices.adapters.simulator import FakeDeviceAdapter
from apps.devices.adapters.stubs import (
    EsslPullAdapter,
    HikvisionISAPIAdapter,
    SupremaBioStarAdapter,
)
from apps.devices.adapters.zkteco import ZKTecoPushAdapter
from apps.devices.models import Device, DeviceProtocol, DeviceType
from apps.institutions.models import Institution


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka Academy", eiin="998877")


@pytest.mark.django_db
def test_adapter_registry_resolution(institution):
    zk_dev = Device.objects.create(
        institution=institution,
        name="ZK Terminal",
        vendor="ZKTeco",
        protocol=DeviceProtocol.PUSH_ADMS,
        serial_no="ZK001",
    )
    assert isinstance(AdapterRegistry.get_adapter(zk_dev), ZKTecoPushAdapter)

    gen_dev = Device.objects.create(
        institution=institution,
        name="HTTP Terminal",
        vendor="CustomVendor",
        protocol=DeviceProtocol.GENERIC_HTTP,
        serial_no="GEN001",
    )
    assert isinstance(AdapterRegistry.get_adapter(gen_dev), GenericHTTPAdapter)

    sim_dev = Device.objects.create(
        institution=institution,
        name="Sim Terminal",
        vendor="Simulator",
        protocol=DeviceProtocol.SIMULATOR,
        serial_no="SIM001",
    )
    assert isinstance(AdapterRegistry.get_adapter(sim_dev), FakeDeviceAdapter)

    hik_dev = Device.objects.create(
        institution=institution,
        name="Hik Terminal",
        vendor="Hikvision",
        protocol=DeviceProtocol.GENERIC_HTTP,
        serial_no="HIK001",
    )
    assert isinstance(AdapterRegistry.get_adapter(hik_dev), HikvisionISAPIAdapter)

    sup_dev = Device.objects.create(
        institution=institution,
        name="Suprema Terminal",
        vendor="Suprema",
        protocol=DeviceProtocol.GENERIC_HTTP,
        serial_no="SUP001",
    )
    assert isinstance(AdapterRegistry.get_adapter(sup_dev), SupremaBioStarAdapter)

    essl_dev = Device.objects.create(
        institution=institution,
        name="eSSL Terminal",
        vendor="eSSL",
        protocol=DeviceProtocol.PULL_SDK,
        serial_no="ESSL001",
    )
    assert isinstance(AdapterRegistry.get_adapter(essl_dev), EsslPullAdapter)


@pytest.mark.django_db
def test_zkteco_adapter_authentication(institution):
    device = Device.objects.create(
        institution=institution,
        name="ZK Device",
        serial_no="ZK-AUTH-01",
        api_token="secret_token_123",
        protocol=DeviceProtocol.PUSH_ADMS,
    )
    adapter = ZKTecoPushAdapter(device)

    # Valid request
    req_valid = MagicMock()
    req_valid.GET = {"SN": "ZK-AUTH-01", "token": "secret_token_123"}
    req_valid.POST = {}
    req_valid.headers = {}
    assert adapter.authenticate_request(req_valid) is True

    # Wrong SN
    req_wrong_sn = MagicMock()
    req_wrong_sn.GET = {"SN": "OTHER_SN", "token": "secret_token_123"}
    req_wrong_sn.POST = {}
    req_wrong_sn.headers = {}
    assert adapter.authenticate_request(req_wrong_sn) is False

    # Wrong token
    req_wrong_token = MagicMock()
    req_wrong_token.GET = {"SN": "ZK-AUTH-01", "token": "wrong_token"}
    req_wrong_token.POST = {}
    req_wrong_token.headers = {}
    assert adapter.authenticate_request(req_wrong_token) is False


@pytest.mark.django_db
def test_zkteco_adapter_payload_parsing(institution):
    device = Device.objects.create(
        institution=institution,
        name="ZK Device",
        serial_no="ZK-PARSE-01",
        device_type=DeviceType.FINGERPRINT,
    )
    adapter = ZKTecoPushAdapter(device)

    # Format: PIN\tYYYY-MM-DD HH:MM:SS\tSTATUS\tVERIFY\tWORKCODE
    raw_payload = (
        "1001\t2026-03-01 08:30:00\t0\t1\t0\n"
        "1002\t2026-03-01 08:31:15\t0\t15\t0\n"
        "\n"
        "INVALID_LINE\n"
    )

    punches = adapter.parse_push_payload(raw_payload)
    assert len(punches) == 2

    assert punches[0]["raw_user_id"] == "1001"
    assert punches[0]["punch_state"] == "0"
    assert punches[0]["verify_type"] == DeviceType.FINGERPRINT

    assert punches[1]["raw_user_id"] == "1002"
    assert punches[1]["verify_type"] == DeviceType.FACE


@pytest.mark.django_db
def test_zkteco_commands_formatting(institution):
    device = Device.objects.create(
        institution=institution,
        name="ZK Device",
        serial_no="ZK-CMD-01",
    )
    adapter = ZKTecoPushAdapter(device)
    enroll_cmd = adapter.format_enroll_command("101", "Rahim", "CARD123")
    assert "DATA USER PIN=101" in enroll_cmd
    assert "Name=Rahim" in enroll_cmd
    assert "Card=CARD123" in enroll_cmd

    del_cmd = adapter.format_delete_command("101")
    assert del_cmd == "DATA DELETE USER PIN=101"


@pytest.mark.django_db
def test_generic_http_adapter_hmac_auth(institution):
    secret = "my_hmac_secret_key"
    device = Device.objects.create(
        institution=institution,
        name="Generic Device",
        serial_no="GEN-HMAC-01",
        auth_secret=secret,
        protocol=DeviceProtocol.GENERIC_HTTP,
    )
    adapter = GenericHTTPAdapter(device)

    body = b'{"events": []}'
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    req = MagicMock()
    req.body = body
    req.headers = {"X-Signature": signature}
    req.data = {}
    assert adapter.authenticate_request(req) is True

    # Bad signature
    req_bad = MagicMock()
    req_bad.body = body
    req_bad.headers = {"X-Signature": "invalid_signature"}
    req_bad.data = {}
    assert adapter.authenticate_request(req_bad) is False


@pytest.mark.django_db
def test_generic_http_adapter_payload_parsing(institution):
    device = Device.objects.create(
        institution=institution,
        name="Generic Device",
        serial_no="GEN-PARSE-01",
        protocol=DeviceProtocol.GENERIC_HTTP,
    )
    adapter = GenericHTTPAdapter(device)

    payload = {
        "punches": [
            {
                "user_id": "901",
                "timestamp": "2026-03-01T08:00:00Z",
                "punch_type": "in",
                "method": "rfid",
            }
        ]
    }
    punches = adapter.parse_push_payload(payload)
    assert len(punches) == 1
    assert punches[0]["raw_user_id"] == "901"
    assert punches[0]["verify_type"] == "rfid"
