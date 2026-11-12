"""Unit tests for SMS gateways, segmentation, and adapters."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.communications.gateways.base import calculate_sms_segments
from apps.communications.gateways.console import ConsoleMockAdapter
from apps.communications.gateways.factory import get_gateway_adapter
from apps.communications.gateways.greenweb import GreenwebAdapter
from apps.communications.gateways.ssl_wireless import SSLWirelessAdapter
from apps.communications.models import SMSGatewayConfig, SMSGatewayProvider
from apps.institutions.models import Institution


@pytest.mark.django_db
class TestSMSSegmentation:
    """Test character encoding detection and GSM/Unicode segmentation."""

    def test_gsm_text_segmentation(self):
        english_short = "Hello, your child was present at school today."
        segments, is_unicode, length = calculate_sms_segments(english_short)
        assert not is_unicode
        assert segments == 1
        assert length == len(english_short)

        # English text exceeding 160 characters
        english_long = "A" * 170
        segments, is_unicode, length = calculate_sms_segments(english_long)
        assert not is_unicode
        assert segments == 2  # (170 / 153) -> 2 segments

    def test_bengali_unicode_segmentation(self):
        bangla_short = "আপনার সন্তানের উপস্থিতি সফলভাবে রেকর্ড করা হয়েছে।"
        segments, is_unicode, length = calculate_sms_segments(bangla_short)
        assert is_unicode
        assert segments == 1  # < 70 chars

        # Bengali text exceeding 70 characters
        bangla_long = "ক" * 80
        segments, is_unicode, length = calculate_sms_segments(bangla_long)
        assert is_unicode
        assert segments == 2  # (80 / 67) -> 2 segments


@pytest.mark.django_db
class TestSMSAdapters:
    """Test individual provider adapters and factory."""

    @pytest.fixture
    def institution(self):
        return Institution.objects.create(
            name_en="Dhaka Model College",
            name_bn="ঢাকা মডেল কলেজ",
        )

    def test_console_mock_adapter(self, institution):
        config = SMSGatewayConfig.objects.create(
            institution=institution,
            name="Mock Gateway",
            provider=SMSGatewayProvider.MOCK_CONSOLE,
            sender_id="MOCK_TEST",
            api_key="mock_key",
            balance=Decimal("250.00"),
            rate_per_segment=Decimal("0.3500"),
        )
        adapter = get_gateway_adapter(config)
        assert isinstance(adapter, ConsoleMockAdapter)

        resp = adapter.send_sms("+8801711122233", "Test Mock SMS")
        assert resp.success
        assert resp.segment_count == 1
        assert resp.cost == Decimal("0.3500")
        assert resp.provider_message_id is not None
        assert adapter.check_balance() == Decimal("250.00")

    @patch("apps.communications.gateways.ssl_wireless.requests.post")
    def test_ssl_wireless_adapter_success(self, mock_post, institution):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"status_code": 200, "status": "SUCCESS", "smsinfo": [{"reference_id": "SSL_REF_9999"}]}'
        mock_resp.json.return_value = {
            "status_code": 200,
            "status": "SUCCESS",
            "smsinfo": [{"reference_id": "SSL_REF_9999"}],
        }
        mock_post.return_value = mock_resp

        config = SMSGatewayConfig.objects.create(
            institution=institution,
            name="SSL Gateway",
            provider=SMSGatewayProvider.SSL_WIRELESS,
            sender_id="DMC_MASK",
            client_id="dmc_user",
            api_key="ssl_token_123",
            balance=Decimal("500.00"),
        )
        adapter = get_gateway_adapter(config)
        assert isinstance(adapter, SSLWirelessAdapter)

        resp = adapter.send_sms("+8801711000000", "SSL Wireless Test")
        assert resp.success
        assert resp.provider_message_id == "SSL_REF_9999"

    @patch("apps.communications.gateways.greenweb.requests.post")
    def test_greenweb_adapter_success(self, mock_post, institution):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Ok: SMS Sent Successfully. SMS ID: GW_555"
        mock_post.return_value = mock_resp

        config = SMSGatewayConfig.objects.create(
            institution=institution,
            name="Greenweb Gateway",
            provider=SMSGatewayProvider.GREENWEB,
            sender_id="GREEN_MASK",
            api_key="gw_token_123",
        )
        adapter = get_gateway_adapter(config)
        assert isinstance(adapter, GreenwebAdapter)

        resp = adapter.send_sms("+8801811000000", "Greenweb Test Message")
        assert resp.success
        assert "GW_555" in (resp.provider_message_id or "")
