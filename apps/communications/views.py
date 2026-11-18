"""DRF ViewSets and API Views for communications."""

from typing import Any

from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.communications.models import (
    ChatThread,
    DeviceToken,
    EmergencyAlert,
    Notice,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    SMSGatewayConfig,
)
from apps.communications.permissions import (
    IsCommunicationsAdmin,
    IsNoticeAdminOrReadOnly,
    IsThreadParticipant,
)
from apps.communications.serializers import (
    ChatMessageSerializer,
    ChatThreadSerializer,
    DeviceTokenSerializer,
    EmergencyAlertSerializer,
    NoticeSerializer,
    NotificationDeliverySerializer,
    NotificationPreferenceSerializer,
    NotificationTemplateSerializer,
    SendDirectSMSSerializer,
    SMSGatewayConfigSerializer,
    TemplatePreviewSerializer,
)
from apps.communications.services.chat_service import send_chat_message
from apps.communications.services.notice_service import get_visible_notices_for_user
from apps.communications.services.notification_service import render_template
from apps.communications.services.sms_service import check_and_update_balance, send_single_sms
from apps.core.mixins import TenantScopedMixin, get_request_institution


@extend_schema_view(
    list=extend_schema(summary="List SMS Gateways"),
    create=extend_schema(summary="Configure New SMS Gateway"),
    retrieve=extend_schema(summary="Retrieve SMS Gateway Details"),
    update=extend_schema(summary="Update SMS Gateway Configuration"),
    destroy=extend_schema(summary="Delete SMS Gateway"),
)
class SMSGatewayConfigViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage SMS gateway providers and credentials."""

    serializer_class = SMSGatewayConfigSerializer
    permission_classes = [IsCommunicationsAdmin]
    queryset = SMSGatewayConfig.objects.all()

    @extend_schema(
        summary="Check Gateway Remote Balance",
        responses={200: OpenApiResponse(description="Balance fetched successfully.")},
    )
    @action(detail=True, methods=["post"], url_path="check-balance")
    def check_balance(self, request: Any, pk: Any = None) -> Response:
        gateway = self.get_object()
        balance = check_and_update_balance(gateway)
        return Response({"balance": str(balance), "currency": "BDT"})

    @extend_schema(
        summary="Send Test SMS",
        request=SendDirectSMSSerializer,
        responses={200: NotificationDeliverySerializer},
    )
    @action(detail=False, methods=["post"], url_path="send-test")
    def send_test_sms(self, request: Any) -> Response:
        serializer = SendDirectSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        institution = get_request_institution(request)
        phone = serializer.validated_data["phone"]
        message = serializer.validated_data["message"]
        gw_id = serializer.validated_data.get("gateway_id")

        gw = self.get_queryset().filter(id=gw_id).first() if gw_id else None
        delivery = send_single_sms(
            institution=institution,
            recipient_phone=phone,
            message=message,
            recipient_user=request.user,
            gateway_config=gw,
        )
        return Response(NotificationDeliverySerializer(delivery).data)


@extend_schema_view(
    list=extend_schema(summary="List Notification Templates"),
    create=extend_schema(summary="Create Notification Template"),
    retrieve=extend_schema(summary="Retrieve Notification Template"),
    update=extend_schema(summary="Update Notification Template"),
    destroy=extend_schema(summary="Delete Notification Template"),
)
class NotificationTemplateViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage bilingual notification message templates."""

    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsCommunicationsAdmin]
    queryset = NotificationTemplate.objects.all()
    filterset_fields = ["code", "channel", "is_active"]
    search_fields = ["name", "code", "body_template_en", "body_template_bn"]

    @extend_schema(
        summary="Preview Rendered Template",
        request=TemplatePreviewSerializer,
        responses={200: OpenApiResponse(description="Rendered template preview.")},
    )
    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request: Any, pk: Any = None) -> Response:
        template = self.get_object()
        serializer = TemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        context_val = serializer.validated_data.get("variables") or serializer.validated_data.get(
            "context", {}
        )
        lang = serializer.validated_data.get("language", "bn")
        subject, body = render_template(template, context_val, lang=lang)

        return Response({"subject": subject, "body": body, "language": lang})


@extend_schema_view(
    list=extend_schema(summary="List Notification Deliveries"),
    retrieve=extend_schema(summary="Retrieve Notification Delivery Details"),
)
class NotificationDeliveryViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Audit log of outbound notifications across SMS, Push, and In-App."""

    queryset = NotificationDelivery.objects.none()
    serializer_class = NotificationDeliverySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["channel", "status", "recipient_phone", "language"]
    search_fields = ["recipient_phone", "content", "title", "provider_message_id"]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return NotificationDelivery.objects.none()
        qs = NotificationDelivery.objects.all()
        user = self.request.user
        if not isinstance(user, User):
            return NotificationDelivery.objects.none()
        if getattr(user, "is_superuser", False):
            return qs
        user_types = getattr(user, "user_types", []) or []
        if {"institution_admin", "principal", "headmaster"} & set(user_types):
            return qs
        # Regular users can only see notifications sent to them
        return qs.filter(recipient_user=user)


@extend_schema_view(
    list=extend_schema(summary="List Device Tokens"),
    create=extend_schema(summary="Register FCM Device Token"),
    destroy=extend_schema(summary="Delete FCM Device Token"),
)
class DeviceTokenViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Register and deregister device FCM push tokens."""

    queryset = DeviceToken.objects.none()
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return DeviceToken.objects.none()
        user = self.request.user
        assert isinstance(user, User)
        return DeviceToken.objects.filter(
            institution=user.institution,
            user=user,
        )

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        token = serializer.validated_data["token"]
        # Update or create to prevent duplicates
        DeviceToken.objects.update_or_create(
            institution=user.institution,
            user=user,
            token=token,
            defaults={
                "device_id": serializer.validated_data.get("device_id", ""),
                "platform": serializer.validated_data.get("platform", "android"),
                "is_active": True,
            },
        )


class NotificationPreferenceView(APIView):
    """Retrieve and update current user's notification preferences."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Current User Preferences",
        responses={200: NotificationPreferenceSerializer},
    )
    def get(self, request: Any) -> Response:
        pref, _ = NotificationPreference.objects.get_or_create(
            institution=get_request_institution(request),
            user=request.user,
        )
        return Response(NotificationPreferenceSerializer(pref).data)

    @extend_schema(
        summary="Update Current User Preferences",
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer},
    )
    def patch(self, request: Any) -> Response:
        pref, _ = NotificationPreference.objects.get_or_create(
            institution=get_request_institution(request),
            user=request.user,
        )
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List Notices"),
    create=extend_schema(summary="Publish Notice"),
    retrieve=extend_schema(summary="Retrieve Notice Details"),
    update=extend_schema(summary="Update Notice"),
    destroy=extend_schema(summary="Delete Notice"),
)
class NoticeViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Notice board management with audience targeting."""

    queryset = Notice.objects.none()
    serializer_class = NoticeSerializer
    permission_classes = [IsNoticeAdminOrReadOnly]
    filterset_fields = ["category", "target_audience", "is_pinned", "is_published"]
    search_fields = ["title_en", "title_bn", "content_en", "content_bn"]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return Notice.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            return Notice.objects.none()
        assert isinstance(user, User)
        institution = getattr(user, "institution", None)
        if not institution:
            return Notice.objects.none()

        if self.action in ["list", "retrieve"]:
            return get_visible_notices_for_user(institution, user)

        # For editing, staff with permissions can manage notices
        return Notice.objects.filter(institution=institution)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        serializer.save(
            institution=user.institution,
            created_by=user,
        )

    @extend_schema(summary="Pin Notice to Top")
    @action(detail=True, methods=["post"], url_path="pin")
    def pin(self, request: Any, pk: Any = None) -> Response:
        notice = self.get_object()
        notice.is_pinned = True
        notice.save(update_fields=["is_pinned"])
        return Response({"status": "pinned"})

    @extend_schema(summary="Unpin Notice from Top")
    @action(detail=True, methods=["post"], url_path="unpin")
    def unpin(self, request: Any, pk: Any = None) -> Response:
        notice = self.get_object()
        notice.is_pinned = False
        notice.save(update_fields=["is_pinned"])
        return Response({"status": "unpinned"})


@extend_schema_view(
    list=extend_schema(summary="List Teacher-Guardian Chat Threads"),
    create=extend_schema(summary="Initiate Chat Thread"),
    retrieve=extend_schema(summary="Retrieve Chat Thread Details"),
)
class ChatThreadViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage 1-on-1 dialogue threads between teachers and guardians."""

    queryset = ChatThread.objects.none()
    serializer_class = ChatThreadSerializer
    permission_classes = [IsAuthenticated, IsThreadParticipant]
    http_method_names = ["get", "post", "retrieve"]

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return ChatThread.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            return ChatThread.objects.none()
        assert isinstance(user, User)
        institution = getattr(user, "institution", None)
        if not institution:
            return ChatThread.objects.none()

        qs = ChatThread.objects.filter(institution=institution)
        if getattr(user, "is_superuser", False) or "institution_admin" in (
            getattr(user, "user_types", []) or []
        ):
            return qs

        # If user is teacher or guardian
        return qs.filter(teacher__user=user) | qs.filter(guardian__user=user)

    @extend_schema(
        summary="List or Send Messages in Thread",
        request=ChatMessageSerializer,
        responses={200: ChatMessageSerializer(many=True), 201: ChatMessageSerializer},
    )
    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request: Any, pk: Any = None) -> Response:
        thread = self.get_object()
        if request.method == "GET":
            msgs = thread.messages.order_by("created_at")
            return Response(ChatMessageSerializer(msgs, many=True).data)

        # POST new message
        content = request.data.get("content", "").strip()
        if not content:
            raise ValidationError({"content": "Message content cannot be empty."})

        msg = send_chat_message(thread, request.user, content)
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Mark Thread Messages as Read")
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request: Any, pk: Any = None) -> Response:
        thread = self.get_object()
        updated = (
            thread.messages.filter(is_read=False)
            .exclude(sender=request.user)
            .update(is_read=True, read_at=timezone.now())
        )
        return Response({"marked_read": updated})


@extend_schema_view(
    list=extend_schema(summary="List Emergency Broadcast Alerts"),
    create=extend_schema(summary="Broadcast Emergency Alert"),
    retrieve=extend_schema(summary="Retrieve Emergency Alert Details"),
)
class EmergencyAlertViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Trigger and audit campus emergency broadcasts overriding quiet hours."""

    serializer_class = EmergencyAlertSerializer
    permission_classes = [IsCommunicationsAdmin]
    http_method_names = ["get", "post", "retrieve"]
    queryset = EmergencyAlert.objects.all()

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        institution = user.institution
        assert institution is not None
        channels = serializer.validated_data.get("channels") or ["sms", "push", "in_app"]

        alert = serializer.save(
            institution=institution,
            sent_by=user,
            channels=channels,
        )

        # Gather target recipients (active users in institution)
        recipients = list(User.objects.filter(institution=institution, is_active=True))
        alert.total_recipients = len(recipients)

        success = 0
        failed = 0

        # Broadcast via SMS/Push with force_override_quiet_hours=True
        msg_text = alert.message_bn or alert.message_en
        for r_user in recipients:
            user_phone = getattr(r_user, "phone", None)
            if "sms" in channels and user_phone:
                deliv = send_single_sms(
                    institution=institution,
                    recipient_phone=str(user_phone),
                    message=f"[EMERGENCY] {msg_text}",
                    recipient_user=r_user,
                )
                if deliv.status == "sent":
                    success += 1
                else:
                    failed += 1

        alert.successful_deliveries = success
        alert.failed_deliveries = failed
        alert.save(update_fields=["total_recipients", "successful_deliveries", "failed_deliveries"])
