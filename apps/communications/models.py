"""Communications models: SMS gateways, templates, deliveries, notices, chat, and alerts."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class SMSGatewayProvider(models.TextChoices):
    SSL_WIRELESS = "ssl_wireless", "SSL Wireless"
    GREENWEB = "greenweb", "Greenweb BD"
    ONNOROKOM = "onnorokom", "Onnorokom SMS"
    TELETALK = "teletalk", "Teletalk Govt"
    MOCK_CONSOLE = "mock_console", "Local / Mock Console"


class SMSGatewayConfig(TenantOwnedModel, SoftDeleteMixin):
    """Tenant-specific credentials and configuration for SMS gateway providers."""

    name = models.CharField(
        max_length=100, help_text="Gateway display name, e.g. 'Primary SSL Wireless'"
    )
    provider = models.CharField(
        max_length=30,
        choices=SMSGatewayProvider.choices,
        default=SMSGatewayProvider.MOCK_CONSOLE,
        db_index=True,
    )
    sender_id = models.CharField(
        max_length=50,
        help_text="Approved BTRC masking alphanumeric sender ID or 11-digit phone number",
    )
    is_masking = models.BooleanField(
        default=False,
        help_text="True if using an approved brand masking name, False for non-masking",
    )
    api_key = models.CharField(max_length=255, help_text="API key, token, or password")
    api_secret = models.CharField(
        max_length=255, blank=True, help_text="Optional API secret or hash"
    )
    client_id = models.CharField(
        max_length=100, blank=True, help_text="Optional client ID, SID, or username"
    )
    endpoint_url = models.URLField(
        blank=True, help_text="Custom gateway HTTP/REST endpoint URL if required"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Default gateway used for outbound SMS dispatch for this institution",
    )
    rate_per_segment = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=Decimal("0.3500"),
        help_text="Cost in BDT per SMS segment (typically ৳0.30 - ৳0.65)",
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Current credited account balance in BDT",
    )
    last_balance_check = models.DateTimeField(null=True, blank=True)
    rate_limit_per_minute = models.PositiveIntegerField(
        default=120,
        help_text="Maximum messages permitted per minute",
    )
    meta_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional provider-specific parameters (e.g. headers, project id)",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "SMS Gateway Config"
        verbose_name_plural = "SMS Gateway Configs"
        ordering = ["-is_default", "name"]

    def __str__(self) -> str:
        masking_str = "Masking" if self.is_masking else "Non-masking"
        return f"{self.name} ({self.get_provider_display()} - {masking_str})"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default gateway per institution
            SMSGatewayConfig.objects.filter(
                institution=self.institution,
                is_default=True,
            ).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)


class SMSBalanceLog(TenantOwnedModel):
    """Audit history of balance checks and account recharges for SMS gateways."""

    gateway = models.ForeignKey(
        SMSGatewayConfig,
        on_delete=models.CASCADE,
        related_name="balance_logs",
    )
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2)
    delta = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(
        max_length=50,
        help_text="Reason: check, recharge, deduction, or manual_adjustment",
    )
    note = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "SMS Balance Log"
        verbose_name_plural = "SMS Balance Logs"
        ordering = ["-created_at"]


class NotificationChannel(models.TextChoices):
    SMS = "sms", "SMS"
    PUSH = "push", "Push Notification"
    EMAIL = "email", "Email"
    IN_APP = "in_app", "In-App Notice"
    ALL = "all", "All Channels"


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"


class NotificationTemplate(TenantOwnedModel, SoftDeleteMixin):
    """Bilingual notification message templates with variable substitution."""

    name = models.CharField(max_length=150)
    code = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Unique event code, e.g. attendance_absent, fee_due, otp_verification",
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.ALL,
    )
    subject_template = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional subject line template for push/email",
    )
    body_template_en = models.TextField(
        help_text="English message body with {{variables}}",
    )
    body_template_bn = models.TextField(
        help_text="Bengali message body with {{variables}}",
    )
    variables_schema = models.JSONField(
        default=list,
        blank=True,
        help_text="List of accepted placeholder keys, e.g. ['student_name', 'amount', 'date']",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=models.Q(is_deleted=False),
                name="unique_active_template_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class NotificationEvent(TenantOwnedModel):
    """Audit log of high-level business events triggering notifications."""

    event_type = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Event type, e.g. attendance_absent, fee_invoice_issued, exam_result",
    )
    source_module = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Originating app: attendance, fees, exams, communications",
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of the originating model instance (Invoice, AttendanceRecord, Result, etc.)",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Notification Event"
        verbose_name_plural = "Notification Events"
        ordering = ["-created_at"]


class NotificationDelivery(TenantOwnedModel):
    """Per-recipient delivery log and audit trail across SMS, Push, Email, and In-App."""

    event = models.ForeignKey(
        NotificationEvent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notification_deliveries",
    )
    recipient_phone = models.CharField(max_length=25, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    language = models.CharField(
        max_length=5,
        default="bn",
        choices=[("bn", "Bangla"), ("en", "English")],
    )
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.QUEUED,
        db_index=True,
    )
    gateway_config = models.ForeignKey(
        SMSGatewayConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    provider_message_id = models.CharField(max_length=150, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    segment_count = models.PositiveIntegerField(default=1)
    cost_bdt = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal("0.0000"),
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Notification Delivery"
        verbose_name_plural = "Notification Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution", "status", "channel"]),
            models.Index(fields=["recipient_phone", "-created_at"]),
        ]


class DevicePlatform(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"


class DeviceToken(TenantOwnedModel):
    """User device tokens for Firebase Cloud Messaging (FCM) mobile push alerts."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.TextField(help_text="FCM registration token string")
    device_id = models.CharField(max_length=150, blank=True)
    platform = models.CharField(
        max_length=20,
        choices=DevicePlatform.choices,
        default=DevicePlatform.ANDROID,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "token"],
                name="unique_user_device_token",
            )
        ]


class NotificationPreference(TenantOwnedModel):
    """User channel and quiet hour preferences."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    enable_sms = models.BooleanField(default=True)
    enable_push = models.BooleanField(default=True)
    enable_email = models.BooleanField(default=True)
    enable_in_app = models.BooleanField(default=True)
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text="If True, suppress non-emergency notifications during night hours",
    )
    quiet_hours_start = models.TimeField(null=True, blank=True, default="22:00:00")
    quiet_hours_end = models.TimeField(null=True, blank=True, default="07:00:00")
    language_preference = models.CharField(
        max_length=5,
        default="bn",
        choices=[("bn", "Bangla"), ("en", "English")],
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"


class NoticeCategory(models.TextChoices):
    GENERAL = "general", "General Announcement"
    ACADEMIC = "academic", "Academic"
    EXAM = "exam", "Examination"
    FEE = "fee", "Fee & Payment"
    HOLIDAY = "holiday", "Holiday"
    EMERGENCY = "emergency", "Emergency"


class NoticeAudience(models.TextChoices):
    ALL = "all", "Entire School"
    STUDENTS = "students", "All Students"
    GUARDIANS = "guardians", "All Guardians"
    TEACHERS = "teachers", "All Teachers"
    STAFF = "staff", "All Staff"
    SPECIFIC_CLASS = "specific_class", "Specific Class / Section"


class Notice(TenantOwnedModel, SoftDeleteMixin):
    """Notice board publications with role and class-level audience targeting."""

    title_en = models.CharField(max_length=255)
    title_bn = models.CharField(max_length=255, blank=True)
    content_en = models.TextField()
    content_bn = models.TextField(blank=True)
    category = models.CharField(
        max_length=30,
        choices=NoticeCategory.choices,
        default=NoticeCategory.GENERAL,
        db_index=True,
    )
    target_audience = models.CharField(
        max_length=30,
        choices=NoticeAudience.choices,
        default=NoticeAudience.ALL,
        db_index=True,
    )
    target_class_level = models.ForeignKey(
        "academics.ClassLevel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    target_section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_pinned = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Pin to the top of notice boards",
    )
    is_published = models.BooleanField(default=True, db_index=True)
    publish_date = models.DateTimeField(default=timezone.now, db_index=True)
    expiry_date = models.DateTimeField(null=True, blank=True, db_index=True)
    attachment = models.FileField(upload_to="notices/", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Notice"
        verbose_name_plural = "Notices"
        ordering = ["-is_pinned", "-publish_date"]


class ChatThread(TenantOwnedModel, SoftDeleteMixin):
    """1-on-1 dialogue thread between a Teacher (Staff) and a Student or Student's Guardian."""

    class ThreadType(models.TextChoices):
        TEACHER_GUARDIAN = "teacher_guardian", "Teacher-Guardian"
        TEACHER_STUDENT = "teacher_student", "Teacher-Student"

    thread_type = models.CharField(
        max_length=30,
        choices=ThreadType.choices,
        default=ThreadType.TEACHER_GUARDIAN,
        db_index=True,
    )
    teacher = models.ForeignKey(
        "staff.Staff",
        on_delete=models.CASCADE,
        related_name="chat_threads_as_teacher",
    )
    guardian = models.ForeignKey(
        "guardians.Guardian",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_threads_as_guardian",
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_threads",
    )
    subject = models.CharField(max_length=200, blank=True)
    is_closed = models.BooleanField(default=False)
    last_message_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("Chat threads cannot be deleted.")

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Chat Thread"
        verbose_name_plural = "Chat Threads"
        ordering = ["-last_message_at"]


class ChatMessage(TenantOwnedModel, SoftDeleteMixin):
    """Individual message exchange inside a chat thread."""

    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages_sent",
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_flagged_for_moderation = models.BooleanField(default=False)
    moderation_note = models.CharField(max_length=255, blank=True)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("Chat messages cannot be deleted.")

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["created_at"]


class EmergencySeverity(models.TextChoices):
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"
    DISASTER = "disaster", "Disaster"


class EmergencyAlert(TenantOwnedModel):
    """Urgent campus-wide alert broadcasting overriding quiet hours."""

    title = models.CharField(max_length=200)
    message_bn = models.TextField()
    message_en = models.TextField(blank=True)
    severity = models.CharField(
        max_length=20,
        choices=EmergencySeverity.choices,
        default=EmergencySeverity.CRITICAL,
    )
    channels = models.JSONField(
        default=list,
        help_text="List of broadcast channels, e.g. ['sms', 'push', 'in_app']",
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    total_recipients = models.PositiveIntegerField(default=0)
    successful_deliveries = models.PositiveIntegerField(default=0)
    failed_deliveries = models.PositiveIntegerField(default=0)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Emergency Alert"
        verbose_name_plural = "Emergency Alerts"
        ordering = ["-sent_at"]
