"""Integration tests for notification services, templates, preferences, and dispatch."""

import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError

from apps.accounts.models import User
from apps.communications.models import (
    DevicePlatform,
    DeviceToken,
    NotificationChannel,
    NotificationPreference,
    NotificationStatus,
    NotificationTemplate,
    SMSGatewayConfig,
    SMSGatewayProvider,
)
from apps.communications.services.notification_service import (
    dispatch_event_notification,
    is_in_quiet_hours,
    render_template,
)
from apps.communications.services.sms_service import send_single_sms
from apps.institutions.models import Institution


@pytest.mark.django_db
class TestNotificationTemplatesAndRendering:
    """Test bilingual template creation and dynamic substitution."""

    @pytest.fixture
    def institution(self):
        return Institution.objects.create(
            name_en="Chittagong High School", name_bn="চট্টগ্রাম হাই স্কুল"
        )

    def test_template_rendering_bilingual(self, institution):
        template = NotificationTemplate.objects.create(
            institution=institution,
            name="Absent Alert",
            code="attendance_absent",
            subject_template="Attendance Notice: {{student_name}}",
            body_template_en="Dear Guardian, {{student_name}} was absent on {{date}}.",
            body_template_bn="শ্রদ্ধেয় অভিভাবক, আপনার সন্তান {{student_name}} {{date}} তারিখে অনুপস্থিত ছিল।",
        )

        ctx = {"student_name": "Rahim", "date": "2026-11-12"}

        subj_bn, body_bn = render_template(template, ctx, lang="bn")
        assert "Rahim" in subj_bn
        assert "Rahim" in body_bn
        assert "অনুপস্থিত" in body_bn

        subj_en, body_en = render_template(template, ctx, lang="en")
        assert "Rahim was absent on 2026-11-12" in body_en

    def test_unique_template_code_per_institution(self, institution):
        NotificationTemplate.objects.create(
            institution=institution,
            name="Fee Due Alert",
            code="fee_due",
            body_template_en="Due",
            body_template_bn="বকেয়া",
        )
        with pytest.raises(IntegrityError):
            NotificationTemplate.objects.create(
                institution=institution,
                name="Duplicate Fee Due",
                code="fee_due",
                body_template_en="Due 2",
                body_template_bn="বকেয়া ২",
            )


@pytest.mark.django_db
class TestQuietHoursAndPreferences:
    """Test user quiet hours and channel preferences."""

    @pytest.fixture
    def user_with_pref(self):
        inst = Institution.objects.create(name_en="Rajshahi Academy", name_bn="রাজশাহী একাডেমি")
        user = User.objects.create_user(
            username="user_pref",
            phone="+8801700112233",
            password="testpassword123",
            institution=inst,
        )
        pref = NotificationPreference.objects.create(
            institution=inst,
            user=user,
            quiet_hours_enabled=True,
            quiet_hours_start=datetime.time(22, 0),  # 10:00 PM
            quiet_hours_end=datetime.time(6, 0),  # 6:00 AM
            language_preference="bn",
        )
        return user, pref

    def test_quiet_hours_spans_midnight(self, user_with_pref):
        _, pref = user_with_pref
        tz = ZoneInfo("Asia/Dhaka")

        # 11:30 PM (23:30) -> Should be inside quiet hours
        night_time = datetime.datetime(2026, 11, 12, 23, 30, tzinfo=tz)
        assert is_in_quiet_hours(pref, check_time=night_time)

        # 04:00 AM -> Should be inside quiet hours
        early_morning = datetime.datetime(2026, 11, 13, 4, 0, tzinfo=tz)
        assert is_in_quiet_hours(pref, check_time=early_morning)

        # 11:00 AM -> Should be outside quiet hours
        daytime = datetime.datetime(2026, 11, 13, 11, 0, tzinfo=tz)
        assert not is_in_quiet_hours(pref, check_time=daytime)


@pytest.mark.django_db
class TestSMSAndPushDispatch:
    """Test full SMS and push notification delivery pipeline."""

    @pytest.fixture
    def setup_data(self):
        inst = Institution.objects.create(
            name_en="Barishal Zilla School", name_bn="বরিশাল জিলা স্কুল"
        )
        gw = SMSGatewayConfig.objects.create(
            institution=inst,
            name="Test Gateway",
            provider=SMSGatewayProvider.MOCK_CONSOLE,
            sender_id="BZS_SMS",
            api_key="mock_key",
            balance=Decimal("100.00"),
            rate_per_segment=Decimal("0.3500"),
            is_default=True,
        )
        user = User.objects.create_user(
            username="user_dispatch",
            phone="+8801811223344",
            password="password123",
            institution=inst,
        )
        DeviceToken.objects.create(
            institution=inst,
            user=user,
            token="fcm_token_device_abc123",
            platform=DevicePlatform.ANDROID,
        )
        return inst, gw, user

    def test_send_single_sms_success_and_balance_deduction(self, setup_data):
        inst, gw, user = setup_data
        initial_balance = gw.balance

        deliv = send_single_sms(
            institution=inst,
            recipient_phone="01811223344",  # local 11-digit format
            message="আপনার সন্তানের ফি জমা হয়েছে।",
            recipient_user=user,
        )

        assert deliv.status == NotificationStatus.SENT
        assert deliv.recipient_phone == "+8801811223344"
        assert deliv.segment_count == 1
        assert deliv.cost_bdt == Decimal("0.3500")

        gw.refresh_from_db()
        assert gw.balance == initial_balance - Decimal("0.3500")

    def test_dispatch_event_respects_user_disabled_sms(self, setup_data):
        inst, _, user = setup_data
        pref, _ = NotificationPreference.objects.get_or_create(
            institution=inst,
            user=user,
        )
        pref.enable_sms = False
        pref.save()

        deliveries = dispatch_event_notification(
            institution=inst,
            event_type="test_event",
            recipient_users=[user],
            context={"title": "Test Title", "message": "Test Body"},
        )

        # SMS channel should not have been created because user disabled SMS
        sms_deliveries = [d for d in deliveries if d.channel == NotificationChannel.SMS]
        assert len(sms_deliveries) == 0

        # Push and In-app should be created
        push_deliveries = [d for d in deliveries if d.channel == NotificationChannel.PUSH]
        assert len(push_deliveries) >= 1
