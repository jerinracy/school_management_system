"""Admin registration for communications models."""

from django.contrib import admin

from apps.communications.models import (
    ChatMessage,
    ChatThread,
    DeviceToken,
    EmergencyAlert,
    Notice,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationTemplate,
    SMSBalanceLog,
    SMSGatewayConfig,
)


@admin.register(SMSGatewayConfig)
class SMSGatewayConfigAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "provider",
        "sender_id",
        "is_masking",
        "is_default",
        "is_active",
        "balance",
        "institution",
    ]
    list_filter = ["provider", "is_masking", "is_default", "is_active"]
    search_fields = ["name", "sender_id", "api_key"]


@admin.register(SMSBalanceLog)
class SMSBalanceLogAdmin(admin.ModelAdmin):
    list_display = [
        "gateway",
        "previous_balance",
        "current_balance",
        "delta",
        "reason",
        "created_at",
    ]
    list_filter = ["reason", "created_at"]


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "channel", "is_active", "institution"]
    list_filter = ["channel", "is_active"]
    search_fields = ["name", "code", "body_template_en", "body_template_bn"]


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "source_module", "reference_id", "created_at", "institution"]
    list_filter = ["source_module", "created_at"]
    search_fields = ["event_type", "reference_id"]


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = [
        "recipient_phone",
        "channel",
        "status",
        "segment_count",
        "cost_bdt",
        "provider_message_id",
        "created_at",
        "institution",
    ]
    list_filter = ["channel", "status", "created_at"]
    search_fields = ["recipient_phone", "content", "provider_message_id"]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "is_active", "last_seen_at"]
    list_filter = ["platform", "is_active"]
    search_fields = ["token", "user__phone"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "enable_sms",
        "enable_push",
        "quiet_hours_enabled",
        "language_preference",
    ]
    list_filter = ["enable_sms", "enable_push", "quiet_hours_enabled", "language_preference"]


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = [
        "title_en",
        "category",
        "target_audience",
        "is_pinned",
        "is_published",
        "publish_date",
        "institution",
    ]
    list_filter = ["category", "target_audience", "is_pinned", "is_published"]
    search_fields = ["title_en", "title_bn", "content_en", "content_bn"]


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ["sender", "content", "is_read", "read_at", "created_at"]


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ["teacher", "guardian", "student", "is_closed", "last_message_at", "institution"]
    list_filter = ["is_closed"]
    inlines = [ChatMessageInline]


@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "severity",
        "sent_by",
        "sent_at",
        "total_recipients",
        "successful_deliveries",
        "failed_deliveries",
    ]
    list_filter = ["severity", "sent_at"]
