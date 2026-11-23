"""DRF ViewSets and API Views for communications."""

from typing import Any

from django.db.models import Q, QuerySet
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
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


def _resolve_thread_participants(
    user: Any, data: dict, institution: Any
) -> tuple[Any, Any, Any, str]:
    """Helper to resolve teacher, student, guardian, and thread type for chat thread creation."""
    teacher_id = data.get("teacher")
    thread_type = data.get("thread_type")

    # 1. If initiating user is a student
    student = getattr(user, "student_profile", None)
    if not student and (
        getattr(user, "user_type", None) == "student"
        or "student" in (getattr(user, "user_types", []) or [])
    ):
        from apps.students.models import Student

        student = Student.objects.filter(institution=institution, phone=user.phone).first()
        if student and not student.user:
            student.user = user
            student.save(update_fields=["user"])

    if student:
        return teacher_id, student, None, ChatThread.ThreadType.TEACHER_STUDENT

    # 2. If initiating user is a guardian
    if hasattr(user, "guardian_profiles") and user.guardian_profiles.exists():
        guardian = user.guardian_profiles.first()
        student_id = data.get("student")
        student_obj = None
        if student_id:
            from apps.students.models import Student

            student_obj = Student.objects.filter(id=student_id, institution=institution).first()
        return teacher_id, student_obj, guardian, ChatThread.ThreadType.TEACHER_GUARDIAN

    # 3. If initiating user is staff/teacher or admin
    if hasattr(user, "staff_profile") and user.staff_profile:
        teacher_id = teacher_id or str(user.staff_profile.id)

    student_id = data.get("student")
    student_obj = None
    if student_id:
        from apps.students.models import Student

        student_obj = Student.objects.filter(id=student_id, institution=institution).first()

    guardian_id = data.get("guardian")
    guardian_obj = None
    if guardian_id:
        from apps.guardians.models import Guardian

        guardian_obj = Guardian.objects.filter(id=guardian_id, institution=institution).first()

    if thread_type == ChatThread.ThreadType.TEACHER_STUDENT or (student_obj and not guardian_obj):
        resolved_type = ChatThread.ThreadType.TEACHER_STUDENT
        guardian_obj = None  # Ensure guardian is strictly None for student thread
    else:
        resolved_type = ChatThread.ThreadType.TEACHER_GUARDIAN

    return teacher_id, student_obj, guardian_obj, resolved_type


@extend_schema_view(
    list=extend_schema(summary="List Teacher-Guardian Chat Threads"),
    create=extend_schema(summary="Initiate Chat Thread"),
    retrieve=extend_schema(summary="Retrieve Chat Thread Details"),
)
class ChatThreadViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage 1-on-1 dialogue threads between teachers, guardians, and students."""

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

        qs = ChatThread.objects.filter(institution=institution).select_related(
            "teacher", "guardian", "student"
        )
        if getattr(user, "is_superuser", False) or "institution_admin" in (
            getattr(user, "user_types", []) or []
        ):
            base_qs = qs
        else:
            # If user is teacher, guardian, or student
            q = Q(teacher__user=user)
            if hasattr(user, "guardian_profiles") and user.guardian_profiles.exists():
                q |= Q(guardian__user=user)
                if user.phone:
                    q |= Q(guardian__phone=user.phone)

            # Student resolution with phone fallback
            student = getattr(user, "student_profile", None)
            if not student and (
                getattr(user, "user_type", None) == "student"
                or "student" in (getattr(user, "user_types", []) or [])
            ):
                from apps.students.models import Student

                student = Student.objects.filter(institution=institution, phone=user.phone).first()
                if student and not student.user:
                    student.user = user
                    student.save(update_fields=["user"])

            if student:
                q |= Q(student=student, thread_type=ChatThread.ThreadType.TEACHER_STUDENT)
                q |= Q(student__user=user, thread_type=ChatThread.ThreadType.TEACHER_STUDENT)

            base_qs = qs.filter(q).distinct()

        # Session filtering: default to active session if not explicitly provided
        session_id = self.request.query_params.get("session") or self.request.headers.get(
            "X-Academic-Session"
        )
        if session_id and session_id != "all":
            base_qs = base_qs.filter(session_id=session_id)
        elif not session_id:
            from apps.institutions.selectors import get_current_academic_session

            current_session = get_current_academic_session(institution.id)
            if current_session:
                base_qs = base_qs.filter(session_id=current_session.id)

        return base_qs

    def perform_create(self, serializer: Any) -> None:
        from apps.core.mixins import get_request_institution
        from apps.institutions.selectors import get_current_academic_session

        institution = get_request_institution(self.request)
        session_id = self.request.data.get("session")
        if not session_id:
            curr = get_current_academic_session(institution.id)
            session_id = curr.id if curr else None
        serializer.save(institution=institution, session_id=session_id)

    def create(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        institution = getattr(user, "institution", None)
        teacher_id, student, guardian, thread_type = _resolve_thread_participants(
            user, request.data, institution
        )

        if not teacher_id:
            raise ValidationError({"teacher": "Teacher ID is required."})

        existing = ChatThread.objects.filter(
            institution=institution,
            teacher_id=teacher_id,
            student=student,
            guardian=guardian,
            thread_type=thread_type,
        ).first()

        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        thread = serializer.save(
            institution=institution,
            teacher_id=teacher_id,
            student=student,
            guardian=guardian,
            thread_type=thread_type,
        )
        return Response(self.get_serializer(thread).data, status=status.HTTP_201_CREATED)

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

    @extend_schema(
        summary="Real-time Chat Webhook Intake and Dispatch Status",
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(
        detail=False,
        methods=["get", "post"],
        url_path="webhook",
        permission_classes=[AllowAny],
    )
    def webhook(self, request: Any) -> Response:
        """Webhook endpoint for real-time external chat integration / sync callbacks."""
        if request.method == "POST":
            payload = request.data
            event_type = payload.get("event", "chat_sync")
            return Response(
                {
                    "status": "received",
                    "event": event_type,
                    "timestamp": timezone.now().isoformat(),
                }
            )
        return Response({"status": "ok", "service": "chat_webhook", "active": True})


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
