"""Serializers for the communications module."""

from typing import Any

from rest_framework import serializers

from apps.communications.models import (
    ChatMessage,
    ChatThread,
    DeviceToken,
    EmergencyAlert,
    Notice,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    SMSBalanceLog,
    SMSGatewayConfig,
)


class SMSGatewayConfigSerializer(serializers.ModelSerializer):
    """Serializer for SMS Gateway credentials and configuration."""

    api_key = serializers.CharField(write_only=True, required=True)
    api_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SMSGatewayConfig
        fields = [
            "id",
            "name",
            "provider",
            "sender_id",
            "is_masking",
            "api_key",
            "api_secret",
            "api_key_masked",
            "client_id",
            "endpoint_url",
            "is_active",
            "is_default",
            "rate_per_segment",
            "balance",
            "last_balance_check",
            "rate_limit_per_minute",
            "meta_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "balance", "last_balance_check", "created_at", "updated_at"]

    def get_api_key_masked(self, obj: SMSGatewayConfig) -> str:
        if not obj.api_key:
            return ""
        if len(obj.api_key) <= 6:
            return "******"
        return f"{obj.api_key[:3]}****{obj.api_key[-3:]}"


class SMSBalanceLogSerializer(serializers.ModelSerializer):
    """Audit log serializer for SMS gateway balance changes."""

    class Meta:
        model = SMSBalanceLog
        fields = [
            "id",
            "gateway",
            "previous_balance",
            "current_balance",
            "delta",
            "reason",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for bilingual notification templates."""

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "code",
            "channel",
            "subject_template",
            "body_template_en",
            "body_template_bn",
            "variables_schema",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TemplatePreviewSerializer(serializers.Serializer):
    """Serializer for testing template substitution."""

    variables = serializers.DictField(child=serializers.CharField(), required=True)
    language = serializers.ChoiceField(choices=["bn", "en"], default="bn")


class NotificationDeliverySerializer(serializers.ModelSerializer):
    """Serializer for notification audit and delivery history."""

    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = NotificationDelivery
        fields = [
            "id",
            "event",
            "recipient_user",
            "recipient_name",
            "recipient_phone",
            "recipient_email",
            "channel",
            "title",
            "content",
            "language",
            "status",
            "gateway_config",
            "provider_message_id",
            "error_message",
            "segment_count",
            "cost_bdt",
            "sent_at",
            "delivered_at",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_recipient_name(self, obj: NotificationDelivery) -> str:
        if obj.recipient_user:
            name = (
                getattr(obj.recipient_user, "get_full_name", lambda: "")()
                or obj.recipient_user.phone
            )
            return str(name or "")
        return ""


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for user device push registration."""

    class Meta:
        model = DeviceToken
        fields = [
            "id",
            "user",
            "token",
            "device_id",
            "platform",
            "is_active",
            "last_seen_at",
        ]
        read_only_fields = ["id", "user", "last_seen_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """User notification preference settings."""

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "user",
            "enable_sms",
            "enable_push",
            "enable_email",
            "enable_in_app",
            "quiet_hours_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "language_preference",
        ]
        read_only_fields = ["id", "user"]


class NoticeSerializer(serializers.ModelSerializer):
    """Serializer for School Notice board posts."""

    created_by_name = serializers.SerializerMethodField()
    class_level_name = serializers.CharField(source="target_class_level.name", read_only=True)
    section_name = serializers.CharField(source="target_section.name", read_only=True)

    class Meta:
        model = Notice
        fields = [
            "id",
            "title_en",
            "title_bn",
            "content_en",
            "content_bn",
            "category",
            "target_audience",
            "target_class_level",
            "class_level_name",
            "target_section",
            "section_name",
            "is_pinned",
            "is_published",
            "publish_date",
            "expiry_date",
            "attachment",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            data = dict(data)
            if "title" in data:
                if not data.get("title_en"):
                    data["title_en"] = data["title"]
                if not data.get("title_bn"):
                    data["title_bn"] = data["title"]
            if "body" in data or "content" in data:
                content_val = data.get("body") or data.get("content")
                if not data.get("content_en"):
                    data["content_en"] = content_val
                if not data.get("content_bn"):
                    data["content_bn"] = content_val
        return super().to_internal_value(data)

    def get_created_by_name(self, obj: Notice) -> str:
        if obj.created_by:
            name = getattr(obj.created_by, "get_full_name", lambda: "")() or obj.created_by.phone
            return str(name or "")
        return ""


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages within a thread."""

    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "thread",
            "sender",
            "sender_name",
            "content",
            "is_read",
            "read_at",
            "is_flagged_for_moderation",
            "moderation_note",
            "created_at",
        ]
        read_only_fields = ["id", "sender", "is_read", "read_at", "created_at"]

    def get_sender_name(self, obj: ChatMessage) -> str:
        name = getattr(obj.sender, "get_full_name", lambda: "")() or obj.sender.phone
        return str(name or "")


class ChatThreadSerializer(serializers.ModelSerializer):
    """Serializer for Teacher ↔ Guardian and Teacher ↔ Student chat threads."""

    teacher_name = serializers.SerializerMethodField()
    teacher_name_bn = serializers.SerializerMethodField()
    teacher_designation = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="student.name_en", read_only=True)
    student_roll = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()
    section_id = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            "id",
            "thread_type",
            "teacher",
            "teacher_name",
            "teacher_name_bn",
            "teacher_designation",
            "guardian",
            "guardian_name",
            "student",
            "student_name",
            "student_roll",
            "class_name",
            "section_name",
            "section_id",
            "subject",
            "session",
            "is_closed",
            "last_message_at",
            "last_message",
            "unread_count",
            "created_at",
        ]
        read_only_fields = ["id", "last_message_at", "created_at"]
        extra_kwargs = {
            "guardian": {"required": False, "allow_null": True},
            "student": {"required": False, "allow_null": True},
            "session": {"required": False, "allow_null": True},
        }

    def get_teacher_name(self, obj: ChatThread) -> str:
        return getattr(obj.teacher, "full_name_en", "") or getattr(obj.teacher, "name_en", "")

    def get_teacher_name_bn(self, obj: ChatThread) -> str:
        if not obj.teacher:
            return ""
        return getattr(obj.teacher, "full_name_bn", "") or getattr(obj.teacher, "name_bn", "")

    def get_teacher_designation(self, obj: ChatThread) -> str:
        if not obj.teacher:
            return ""
        desig = getattr(obj.teacher, "designation", None)
        if desig:
            return getattr(desig, "title", "") or getattr(desig, "title_bn", "") or str(desig)
        return ""

    def get_guardian_name(self, obj: ChatThread) -> str:
        return getattr(obj.guardian, "name_en", "") if obj.guardian else ""

    def get_student_roll(self, obj: ChatThread) -> str:
        if not obj.student:
            return ""
        enrollment = (
            obj.student.enrollments.filter(status="active").first()
            or obj.student.enrollments.first()
        )
        if enrollment and enrollment.roll_no is not None:
            return str(enrollment.roll_no)
        return ""

    def get_class_name(self, obj: ChatThread) -> str:
        if not obj.student:
            return ""
        enrollment = (
            obj.student.enrollments.filter(status="active").select_related("class_level").first()
        )
        return enrollment.class_level.name if enrollment and enrollment.class_level else ""

    def get_section_name(self, obj: ChatThread) -> str:
        if not obj.student:
            return ""
        enrollment = (
            obj.student.enrollments.filter(status="active").select_related("section").first()
        )
        return enrollment.section.name if enrollment and enrollment.section else ""

    def get_section_id(self, obj: ChatThread) -> str:
        if not obj.student:
            return ""
        enrollment = (
            obj.student.enrollments.filter(status="active").first()
            or obj.student.enrollments.first()
        )
        return str(enrollment.section_id) if enrollment and enrollment.section_id else ""

    def get_last_message(self, obj: ChatThread) -> str:
        last = obj.messages.order_by("-created_at").first()
        return last.content if last else ""

    def get_unread_count(self, obj: ChatThread) -> int:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=user).count()


class EmergencyAlertSerializer(serializers.ModelSerializer):
    """Serializer for campus-wide emergency broadcasts."""

    sent_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyAlert
        fields = [
            "id",
            "title",
            "message_bn",
            "message_en",
            "severity",
            "channels",
            "sent_by",
            "sent_by_name",
            "sent_at",
            "total_recipients",
            "successful_deliveries",
            "failed_deliveries",
        ]
        read_only_fields = [
            "id",
            "sent_by",
            "sent_at",
            "total_recipients",
            "successful_deliveries",
            "failed_deliveries",
        ]

    def get_sent_by_name(self, obj: EmergencyAlert) -> str:
        if obj.sent_by:
            name = getattr(obj.sent_by, "get_full_name", lambda: "")() or obj.sent_by.phone
            return str(name or "")
        return ""


class SendDirectSMSSerializer(serializers.Serializer):
    """Serializer for ad-hoc manual SMS testing."""

    phone = serializers.CharField(max_length=25, required=True)
    message = serializers.CharField(max_length=1000, required=True)
    gateway_id = serializers.UUIDField(required=False, allow_null=True)
