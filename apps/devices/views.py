"""API Views and Webhook Endpoints for Attendance Hardware Integration."""

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import TenantScopedMixin
from apps.devices.adapters.base import AdapterRegistry
from apps.devices.models import (
    BiometricConsent,
    BiometricEnrollment,
    CommandStatus,
    Device,
    DeviceCommand,
    DeviceGroup,
    DeviceGroupMember,
    DeviceHealthLog,
    DeviceStatus,
    DeviceUserMap,
    RawPunch,
    RawPunchStatus,
)
from apps.devices.permissions import (
    CanManageDevices,
    CanManagePunches,
    CanViewDevices,
    CanViewPunches,
)
from apps.devices.serializers import (
    BiometricConsentSerializer,
    BiometricEnrollmentSerializer,
    DeviceCommandSerializer,
    DeviceGroupMemberSerializer,
    DeviceGroupSerializer,
    DeviceHealthLogSerializer,
    DeviceSerializer,
    DeviceUserMapSerializer,
    EnrollUserRequestSerializer,
    RawPunchSerializer,
    ResolveUnmappedPunchSerializer,
)
from apps.devices.services import (
    enroll_user_on_device,
    ingest_raw_punches,
    queue_device_command,
    resolve_unmapped_punch,
    withdraw_biometric_consent,
)
from apps.institutions.models import Institution
from apps.staff.models import Staff
from apps.students.models import Student

logger = logging.getLogger(__name__)


def _get_request_institution(request: Request) -> Institution:
    user = request.user
    if not hasattr(user, "institution") or user.institution is None:
        raise PermissionDenied("User is not associated with an institution.")
    return user.institution


class DeviceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage hardware terminals, groups, and device commands."""

    queryset = Device.objects.select_related("branch").filter(is_deleted=False)
    serializer_class = DeviceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["device_type", "protocol", "status", "branch", "is_active"]
    search_fields = ["name", "serial_no", "model", "location"]
    ordering_fields = ["name", "status", "last_seen", "created_at"]
    ordering = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve", "health_logs"]:
            return [permissions.IsAuthenticated(), (CanViewDevices | CanManageDevices)()]
        return [permissions.IsAuthenticated(), CanManageDevices()]

    @action(detail=True, methods=["post"], url_path="enroll-user")
    def enroll_user(self, request: Request, pk: Any = None) -> Response:
        """Enroll student or staff on device with verified consent."""
        device = self.get_object()
        serializer = EnrollUserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        student = None
        staff = None
        if data.get("student_id"):
            student = get_object_or_404(
                Student, id=data["student_id"], institution=device.institution, is_deleted=False
            )
        if data.get("staff_id"):
            staff = get_object_or_404(
                Staff, id=data["staff_id"], institution=device.institution, is_deleted=False
            )

        try:
            user_map, cmd = enroll_user_on_device(
                device=device,
                user_pin=data["user_pin"],
                user_name=data["user_name"],
                card_no=data.get("card_no", ""),
                student=student,
                staff=staff,
                method=data.get("method"),
            )
        except ValueError as err:
            raise ValidationError(str(err)) from err

        return Response(
            {
                "message": "User enrollment command queued successfully.",
                "user_map_id": str(user_map.id),
                "command_id": str(cmd.id),
                "status": cmd.status,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="queue-command")
    def queue_command(self, request: Request, pk: Any = None) -> Response:
        """Queue a remote hardware instruction."""
        device = self.get_object()
        command_type = request.data.get("command_type")
        payload = request.data.get("payload", "")

        if not command_type:
            raise ValidationError({"command_type": "command_type is required."})

        cmd = queue_device_command(device=device, command_type=command_type, payload=payload)
        return Response(DeviceCommandSerializer(cmd).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request: Request, pk: Any = None) -> Response:
        """Test terminal heartbeat or simulator ping."""
        device = self.get_object()
        now = timezone.now()

        # Update last seen and health status
        device.last_seen = now
        device.status = DeviceStatus.ONLINE
        device.save(update_fields=["last_seen", "status", "updated_at"])

        DeviceHealthLog.objects.create(
            institution=device.institution,
            device=device,
            device_time=now,
            clock_drift_seconds=0,
            ip_address=device.ip_address,
            status_ok=True,
            raw_data=f"Manual connection test at {now.isoformat()}",
        )

        return Response(
            {
                "status": "online",
                "device": device.name,
                "vendor": device.vendor,
                "serial_no": device.serial_no,
                "last_seen": device.last_seen.isoformat(),
            }
        )

    @action(detail=True, methods=["get"], url_path="health-logs")
    def health_logs(self, request: Request, pk: Any = None) -> Response:
        """Retrieve recent diagnostic telemetry for terminal."""
        device = self.get_object()
        logs = DeviceHealthLog.objects.filter(device=device).order_by("-created_at")[:50]
        return Response(DeviceHealthLogSerializer(logs, many=True).data)


class DeviceGroupViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Logical perimeter groupings of terminals."""

    queryset = DeviceGroup.objects.prefetch_related("members__device").filter(is_deleted=False)
    serializer_class = DeviceGroupSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["target_audience"]
    search_fields = ["name", "description"]
    ordering = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewDevices | CanManageDevices)()]
        return [permissions.IsAuthenticated(), CanManageDevices()]

    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request: Request, pk: Any = None) -> Response:
        """Add a terminal to this group."""
        group = self.get_object()
        device_id = request.data.get("device_id")
        if not device_id:
            raise ValidationError({"device_id": "device_id is required."})

        device = get_object_or_404(
            Device, id=device_id, institution=group.institution, is_deleted=False
        )
        member, _ = DeviceGroupMember.objects.get_or_create(
            group=group,
            device=device,
            defaults={"institution": group.institution},
        )
        return Response(DeviceGroupMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="remove-member")
    def remove_member(self, request: Request, pk: Any = None) -> Response:
        """Remove a terminal from this group."""
        group = self.get_object()
        device_id = request.data.get("device_id")
        if not device_id:
            raise ValidationError({"device_id": "device_id is required."})

        DeviceGroupMember.objects.filter(group=group, device_id=device_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeviceUserMapViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Device PIN mappings to school persons."""

    queryset = DeviceUserMap.objects.select_related("device", "student", "staff").all()
    serializer_class = DeviceUserMapSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["device", "user_type", "student", "staff"]
    search_fields = ["device_user_id", "rfid_card", "student__name_en", "staff__full_name_en"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewDevices | CanManageDevices)()]
        return [permissions.IsAuthenticated(), CanManageDevices()]


class BiometricConsentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Guardian and employee consent management."""

    queryset = BiometricConsent.objects.select_related("student", "staff", "guardian").filter(
        is_deleted=False
    )
    serializer_class = BiometricConsentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["subject_type", "student", "staff", "guardian"]
    search_fields = ["student__name_en", "staff__full_name_en", "guardian__name_en"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewDevices | CanManageDevices)()]
        return [permissions.IsAuthenticated(), CanManageDevices()]

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request: Request, pk: Any = None) -> Response:
        """Withdraw consent and queue hardware user deletions."""
        consent = self.get_object()
        if not consent.is_active:
            raise ValidationError("Consent is already withdrawn.")
        withdraw_biometric_consent(consent)
        return Response(BiometricConsentSerializer(consent).data)


class BiometricEnrollmentViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Terminal enrollment metadata records (NO templates stored)."""

    queryset = BiometricEnrollment.objects.select_related(
        "student", "staff", "device", "consent"
    ).filter(is_deleted=False)
    serializer_class = BiometricEnrollmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["device", "subject_type", "method", "is_active"]
    search_fields = ["device_user_id", "student__name_en", "staff__full_name_en"]

    def get_permissions(self) -> list[Any]:
        return [permissions.IsAuthenticated(), (CanViewDevices | CanManageDevices)()]


class DeviceCommandViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Audit view for dispatched hardware instructions."""

    queryset = DeviceCommand.objects.select_related("device").all()
    serializer_class = DeviceCommandSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["device", "status", "command_type"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list[Any]:
        return [permissions.IsAuthenticated(), (CanViewDevices | CanManageDevices)()]


class RawPunchViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Immutable audit trail of raw biometric scans."""

    queryset = RawPunch.objects.select_related("device", "resolved_student", "resolved_staff").all()
    serializer_class = RawPunchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["device", "status", "verify_type", "punch_state", "raw_user_id"]
    search_fields = ["raw_user_id", "serial_no"]
    ordering_fields = ["device_time", "received_at", "clock_drift_seconds"]
    ordering = ["-device_time"]

    def get_permissions(self) -> list[Any]:
        return [permissions.IsAuthenticated(), (CanViewPunches | CanManagePunches)()]


class UnmappedPunchViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Review queue for punches with unrecognized hardware user PINs."""

    queryset = (
        RawPunch.objects.filter(status=RawPunchStatus.UNMAPPED)
        .select_related("device")
        .order_by("-device_time")
    )
    serializer_class = RawPunchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["device", "verify_type"]
    search_fields = ["raw_user_id", "serial_no"]

    def get_permissions(self) -> list[Any]:
        return [permissions.IsAuthenticated(), (CanViewPunches | CanManagePunches)()]

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request: Request, pk: Any = None) -> Response:
        """Resolve unmapped punch to person and create persistent PIN mapping."""
        raw_punch = self.get_object()
        serializer = ResolveUnmappedPunchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        student = None
        staff = None
        if data.get("student_id"):
            student = get_object_or_404(
                Student, id=data["student_id"], institution=raw_punch.institution, is_deleted=False
            )
        if data.get("staff_id"):
            staff = get_object_or_404(
                Staff, id=data["staff_id"], institution=raw_punch.institution, is_deleted=False
            )

        resolved_obj = resolve_unmapped_punch(
            raw_punch=raw_punch,
            student=student,
            staff=staff,
            create_mapping=data.get("create_mapping", True),
        )
        return Response(RawPunchSerializer(resolved_obj).data)


# -----------------------------------------------------------------------------
# Hardware Push Protocol & Webhook Endpoints (Direct terminal communication)
# -----------------------------------------------------------------------------


@extend_schema(exclude=True)
class ZKTecoCdataView(APIView):
    """Handles ZKTeco ADMS push protocol: /iclock/cdata."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: HttpRequest) -> HttpResponse:
        """Device heartbeat or ping."""
        sn = request.GET.get("SN")
        if not sn:
            return HttpResponse("ERROR: NO SN", status=400, content_type="text/plain")

        device = Device.objects.filter(serial_no=sn, is_active=True).first()
        if not device:
            return HttpResponse("ERROR: UNKNOWN DEVICE", status=404, content_type="text/plain")

        adapter = AdapterRegistry.get_adapter(device)
        if not adapter.authenticate_request(request):
            return HttpResponse("ERROR: AUTH", status=401, content_type="text/plain")

        # Update heartbeat
        now = timezone.now()
        device.last_seen = now
        device.status = DeviceStatus.ONLINE
        device.save(update_fields=["last_seen", "status", "updated_at"])

        return HttpResponse("OK", content_type="text/plain")

    def post(self, request: HttpRequest) -> HttpResponse:
        """Device ATTLOG upload."""
        sn = request.GET.get("SN") or request.POST.get("SN")
        if not sn:
            return HttpResponse("ERROR: NO SN", status=400, content_type="text/plain")

        device = Device.objects.filter(serial_no=sn, is_active=True).first()
        if not device:
            return HttpResponse("ERROR: UNKNOWN DEVICE", status=404, content_type="text/plain")

        adapter = AdapterRegistry.get_adapter(device)
        if not adapter.authenticate_request(request):
            return HttpResponse("ERROR: AUTH", status=401, content_type="text/plain")

        table = request.GET.get("table", "ATTLOG")
        if table != "ATTLOG":
            # Other tables (OPERLOG, etc.) acknowledged
            return HttpResponse("OK", content_type="text/plain")

        punches = adapter.parse_push_payload(request.body)
        created, duplicates, unmapped = ingest_raw_punches(device, punches)

        logger.info(
            "ZKTeco SN %s ingested %d punches (%d dup, %d unmapped)",
            sn,
            created,
            duplicates,
            unmapped,
        )
        return HttpResponse(f"OK: {len(punches)}", content_type="text/plain")


@extend_schema(exclude=True)
class ZKTecoGetRequestView(APIView):
    """Handles ZKTeco command polling: /iclock/getrequest."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: HttpRequest) -> HttpResponse:
        sn = request.GET.get("SN")
        if not sn:
            return HttpResponse("ERROR: NO SN", status=400, content_type="text/plain")

        device = Device.objects.filter(serial_no=sn, is_active=True).first()
        if not device:
            return HttpResponse("ERROR: UNKNOWN DEVICE", status=404, content_type="text/plain")

        adapter = AdapterRegistry.get_adapter(device)
        if not adapter.authenticate_request(request):
            return HttpResponse("ERROR: AUTH", status=401, content_type="text/plain")

        # Find oldest queued command
        cmd = (
            DeviceCommand.objects.filter(device=device, status=CommandStatus.QUEUED)
            .order_by("created_at")
            .first()
        )
        if cmd:
            cmd.status = CommandStatus.SENT
            cmd.sent_at = timezone.now()
            cmd.save(update_fields=["status", "sent_at", "updated_at"])
            # Format: C:{ID}:{PAYLOAD}
            return HttpResponse(f"C:{cmd.id}:{cmd.payload}\n", content_type="text/plain")

        return HttpResponse("OK", content_type="text/plain")


@extend_schema(exclude=True)
class ZKTecoDeviceCmdView(APIView):
    """Handles ZKTeco command execution confirmation: /iclock/devicecmd."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request: HttpRequest) -> HttpResponse:
        sn = request.GET.get("SN") or request.POST.get("SN")
        if not sn:
            return HttpResponse("ERROR: NO SN", status=400, content_type="text/plain")

        device = Device.objects.filter(serial_no=sn, is_active=True).first()
        if not device:
            return HttpResponse("ERROR: UNKNOWN DEVICE", status=404, content_type="text/plain")

        body_str = request.body.decode("utf-8", errors="replace")
        # Format: ID=xxx&Return=0&CMD=xxx
        params: dict[str, str] = {}
        for part in body_str.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip()] = v.strip()

        cmd_id = params.get("ID")
        return_code = params.get("Return", "0")

        if cmd_id:
            try:
                cmd = DeviceCommand.objects.get(id=cmd_id, device=device)
                cmd.status = (
                    CommandStatus.ACKNOWLEDGED if return_code == "0" else CommandStatus.FAILED
                )
                cmd.acknowledged_at = timezone.now()
                cmd.response_message = f"Return={return_code}"
                cmd.save(
                    update_fields=["status", "acknowledged_at", "response_message", "updated_at"]
                )
            except DeviceCommand.DoesNotExist:
                logger.warning("Received command response for unknown command ID: %s", cmd_id)

        return HttpResponse("OK", content_type="text/plain")


@extend_schema(exclude=True)
class GenericWebhookPushView(APIView):
    """Generic JSON Webhook push intake for modern terminals with HMAC verification."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request: HttpRequest) -> HttpResponse:
        serial_no = request.headers.get("X-Device-Serial") or getattr(request, "data", {}).get(
            "serial_no"
        )
        if not serial_no:
            return HttpResponse(
                "ERROR: Missing device serial", status=400, content_type="text/plain"
            )

        device = Device.objects.filter(serial_no=serial_no, is_active=True).first()
        if not device:
            return HttpResponse("ERROR: Unknown device", status=404, content_type="text/plain")

        adapter = AdapterRegistry.get_adapter(device)
        if not adapter.authenticate_request(request):
            return HttpResponse(
                "ERROR: Invalid signature or token", status=401, content_type="text/plain"
            )

        try:
            import json

            payload = json.loads(request.body)
        except Exception:
            payload = getattr(request, "data", {})

        punches = adapter.parse_push_payload(payload)
        created, duplicates, unmapped = ingest_raw_punches(device, punches)

        return Response(
            {
                "status": "success",
                "device": device.name,
                "serial_no": device.serial_no,
                "created": created,
                "duplicates": duplicates,
                "unmapped": unmapped,
            },
            status=status.HTTP_200_OK,
        )
