"""DRF ViewSets for Hostel Management."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.mixins import TenantScopedMixin
from apps.hostel.models import (
    Bed,
    GatePass,
    Hostel,
    HostelAllocation,
    HostelAttendance,
    HostelFeeLink,
    HostelVisitorLog,
    MealAttendance,
    MealPlan,
    Room,
)
from apps.hostel.permissions import (
    CanAccessGatePass,
    CanManageHostel,
    CanManageOrWardenHostel,
    CanReadHostelPortal,
    IsHostelFeatureEnabled,
    has_hostel_staff_permission,
    resolve_guardian_ward_ids,
    resolve_student_for_user,
)
from apps.hostel.serializers import (
    BedSerializer,
    GatePassOtpConfirmSerializer,
    GatePassSerializer,
    HostelAllocationSerializer,
    HostelAttendanceSerializer,
    HostelFeeLinkSerializer,
    HostelRoomSerializer,
    HostelSerializer,
    HostelVisitorLogSerializer,
    MealAttendanceSerializer,
    MealPlanSerializer,
    VacateAllocationSerializer,
)
from apps.hostel.services import (
    allocate_bed,
    approve_gate_pass,
    checkin_gate_pass,
    checkout_gate_pass,
    confirm_gate_pass_otp,
    reject_gate_pass,
    request_gate_pass,
    vacate_allocation,
)


def _ensure_same_tenant(institution_id: Any, obj: Any, field_name: str) -> None:
    if obj is not None and getattr(obj, "institution_id", None) != institution_id:
        raise DRFValidationError({field_name: f"Selected {field_name} belongs to another tenant."})


def _visible_student_ids_for_user(user: User) -> list[Any]:
    student = resolve_student_for_user(user)
    if student is not None:
        return [student.id]
    return resolve_guardian_ward_ids(user)


@extend_schema_view(
    list=extend_schema(summary="List Hostels"),
    retrieve=extend_schema(summary="Get Hostel"),
    create=extend_schema(summary="Create Hostel"),
    partial_update=extend_schema(summary="Update Hostel"),
    destroy=extend_schema(summary="Delete Hostel"),
)
class HostelViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Hostel.objects.select_related("branch", "warden").all()
    serializer_class = HostelSerializer
    filterset_fields = ["branch", "hostel_type", "is_active"]
    search_fields = ["name", "code"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageHostel()]

    def get_queryset(self) -> QuerySet[Hostel]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("branch"), "branch")
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("warden"), "warden")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Rooms"),
    retrieve=extend_schema(summary="Get Hostel Room"),
    create=extend_schema(summary="Create Hostel Room"),
    partial_update=extend_schema(summary="Update Hostel Room"),
    destroy=extend_schema(summary="Delete Hostel Room"),
)
class RoomViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Room.objects.select_related("hostel").all()
    serializer_class = HostelRoomSerializer
    filterset_fields = ["hostel", "is_active"]
    search_fields = ["room_number", "floor"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageHostel()]

    def get_queryset(self) -> QuerySet[Room]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("hostel"), "hostel")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Beds"),
    retrieve=extend_schema(summary="Get Hostel Bed"),
    create=extend_schema(summary="Create Hostel Bed"),
    partial_update=extend_schema(summary="Update Hostel Bed"),
    destroy=extend_schema(summary="Delete Hostel Bed"),
)
class BedViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Bed.objects.select_related("room", "room__hostel").all()
    serializer_class = BedSerializer
    filterset_fields = ["room", "room__hostel", "status"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageHostel()]

    def get_queryset(self) -> QuerySet[Bed]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("room"), "room")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Fee Links"),
    retrieve=extend_schema(summary="Get Hostel Fee Link"),
    create=extend_schema(summary="Create Hostel Fee Link"),
    partial_update=extend_schema(summary="Update Hostel Fee Link"),
    destroy=extend_schema(summary="Delete Hostel Fee Link"),
)
class HostelFeeLinkViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = HostelFeeLink.objects.select_related("fee_head", "hostel", "session").all()
    serializer_class = HostelFeeLinkSerializer
    permission_classes = [IsAuthenticated, IsHostelFeatureEnabled, CanManageHostel]
    filterset_fields = ["hostel", "session", "fee_head"]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("fee_head"), "fee_head"
        )
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("hostel"), "hostel")
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("session"), "session"
        )
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Allocations"),
    retrieve=extend_schema(summary="Get Hostel Allocation"),
    create=extend_schema(summary="Allocate Hostel Bed to Student"),
)
class HostelAllocationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = HostelAllocation.objects.select_related(
        "session", "student", "hostel", "room", "bed"
    ).all()
    serializer_class = HostelAllocationSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["session", "hostel", "room", "is_active", "student"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageOrWardenHostel()]

    def get_queryset(self) -> QuerySet[HostelAllocation]:
        qs = super().get_queryset().filter(is_deleted=False)
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_hostel_staff_permission(self.request, self):
            return qs
        student_ids = _visible_student_ids_for_user(user)
        return qs.filter(student_id__in=student_ids) if student_ids else qs.none()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _ensure_same_tenant(user.institution_id, data.get("session"), "session")
        _ensure_same_tenant(user.institution_id, data.get("student"), "student")
        _ensure_same_tenant(user.institution_id, data.get("bed"), "bed")
        _ensure_same_tenant(user.institution_id, data.get("hostel_fee_link"), "hostel_fee_link")
        try:
            allocation = allocate_bed(
                institution=user.institution,
                session=data["session"],
                student=data["student"],
                bed=data["bed"],
                hostel_fee_link=data.get("hostel_fee_link"),
                allocated_date=data.get("allocated_date"),
                remarks=data.get("remarks", ""),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(allocation).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Vacate Hostel Bed Allocation",
        request=VacateAllocationSerializer,
        responses={200: HostelAllocationSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsHostelFeatureEnabled, CanManageOrWardenHostel],
    )
    def vacate(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        allocation = self.get_object()
        serializer = VacateAllocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = vacate_allocation(
                institution=user.institution,
                allocation=allocation,
                vacated_date=serializer.validated_data.get("vacated_date"),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Attendance Records"),
    retrieve=extend_schema(summary="Get Hostel Attendance Record"),
    create=extend_schema(summary="Record Hostel Night Roll Call / Biometric Event"),
)
class HostelAttendanceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = HostelAttendance.objects.select_related("hostel", "student").all()
    serializer_class = HostelAttendanceSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["hostel", "student", "attendance_date", "event_type", "status"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageOrWardenHostel()]

    def get_queryset(self) -> QuerySet[HostelAttendance]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_hostel_staff_permission(self.request, self):
            return qs
        student_ids = _visible_student_ids_for_user(user)
        return qs.filter(student_id__in=student_ids) if student_ids else qs.none()

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("hostel"), "hostel")
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("student"), "student"
        )
        serializer.save(institution=user.institution, recorded_by=user)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Gate Passes"),
    retrieve=extend_schema(summary="Get Gate Pass"),
    create=extend_schema(summary="Request Gate Pass (Sends Guardian OTP)"),
)
class GatePassViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = GatePass.objects.select_related("student", "hostel", "allocation").all()
    serializer_class = GatePassSerializer
    permission_classes = [IsAuthenticated, IsHostelFeatureEnabled, CanAccessGatePass]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["hostel", "student", "status"]

    def get_queryset(self) -> QuerySet[GatePass]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_hostel_staff_permission(self.request, self):
            return qs
        student_ids = _visible_student_ids_for_user(user)
        return qs.filter(student_id__in=student_ids) if student_ids else qs.none()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        student = data["student"]
        hostel = data["hostel"]
        _ensure_same_tenant(user.institution_id, student, "student")
        _ensure_same_tenant(user.institution_id, hostel, "hostel")

        if not has_hostel_staff_permission(request, self):
            visible_ids = _visible_student_ids_for_user(user)
            if student.id not in visible_ids:
                raise PermissionDenied(
                    "You may only request a gate pass for yourself or your ward."
                )

        try:
            gp, _raw_otp = request_gate_pass(
                institution=user.institution,
                student=student,
                hostel=hostel,
                reason=data["reason"],
                destination=data.get("destination", ""),
                expected_out_at=data["expected_out_at"],
                expected_return_at=data["expected_return_at"],
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(gp).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Confirm Gate Pass with Guardian OTP",
        request=GatePassOtpConfirmSerializer,
        responses={200: GatePassSerializer},
    )
    @action(detail=True, methods=["post"], url_path="confirm-otp")
    def confirm_otp(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        gate_pass = self.get_object()
        if not has_hostel_staff_permission(request, self):
            ward_ids = resolve_guardian_ward_ids(user)
            if gate_pass.student_id not in ward_ids:
                raise PermissionDenied(
                    "Only the student's guardian or hostel staff may confirm OTP."
                )
        serializer = GatePassOtpConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = confirm_gate_pass_otp(
                institution=user.institution,
                gate_pass=gate_pass,
                otp=serializer.validated_data["otp"],
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)

    @extend_schema(summary="Approve Gate Pass", request=None, responses={200: GatePassSerializer})
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsHostelFeatureEnabled, CanManageOrWardenHostel],
    )
    def approve(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        gate_pass = self.get_object()
        try:
            updated = approve_gate_pass(
                institution=user.institution, gate_pass=gate_pass, actor=user
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)

    @extend_schema(summary="Reject Gate Pass", request=None, responses={200: GatePassSerializer})
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsHostelFeatureEnabled, CanManageOrWardenHostel],
    )
    def reject(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        gate_pass = self.get_object()
        try:
            updated = reject_gate_pass(
                institution=user.institution, gate_pass=gate_pass, actor=user
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)

    @extend_schema(summary="Check Out Gate Pass", request=None, responses={200: GatePassSerializer})
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsHostelFeatureEnabled, CanManageOrWardenHostel],
    )
    def checkout(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        gate_pass = self.get_object()
        try:
            updated = checkout_gate_pass(institution=user.institution, gate_pass=gate_pass)
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)

    @extend_schema(summary="Check In Gate Pass", request=None, responses={200: GatePassSerializer})
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsHostelFeatureEnabled, CanManageOrWardenHostel],
    )
    def checkin(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        gate_pass = self.get_object()
        try:
            updated = checkin_gate_pass(institution=user.institution, gate_pass=gate_pass)
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(updated).data)


@extend_schema_view(
    list=extend_schema(summary="List Meal Plans"),
    retrieve=extend_schema(summary="Get Meal Plan"),
    create=extend_schema(summary="Create Meal Plan"),
    partial_update=extend_schema(summary="Update Meal Plan"),
    destroy=extend_schema(summary="Delete Meal Plan"),
)
class MealPlanViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = MealPlan.objects.select_related("hostel").all()
    serializer_class = MealPlanSerializer
    filterset_fields = ["hostel", "meal_type", "is_active"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageOrWardenHostel()]

    def get_queryset(self) -> QuerySet[MealPlan]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("hostel"), "hostel")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Meal Attendance"),
    retrieve=extend_schema(summary="Get Meal Attendance"),
    create=extend_schema(summary="Record Meal Attendance"),
)
class MealAttendanceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = MealAttendance.objects.select_related("meal_plan", "student").all()
    serializer_class = MealAttendanceSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["meal_plan", "student", "meal_date", "consumed"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsHostelFeatureEnabled(), CanReadHostelPortal()]
        return [IsAuthenticated(), IsHostelFeatureEnabled(), CanManageOrWardenHostel()]

    def get_queryset(self) -> QuerySet[MealAttendance]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_hostel_staff_permission(self.request, self):
            return qs
        student_ids = _visible_student_ids_for_user(user)
        return qs.filter(student_id__in=student_ids) if student_ids else qs.none()

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("meal_plan"), "meal_plan"
        )
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("student"), "student"
        )
        serializer.save(institution=user.institution, recorded_by=user)


@extend_schema_view(
    list=extend_schema(summary="List Hostel Visitor Logs"),
    retrieve=extend_schema(summary="Get Hostel Visitor Log"),
    create=extend_schema(summary="Log Hostel Visitor"),
    partial_update=extend_schema(summary="Update Hostel Visitor Log"),
)
class HostelVisitorLogViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = HostelVisitorLog.objects.select_related("hostel", "student").all()
    serializer_class = HostelVisitorLogSerializer
    permission_classes = [IsAuthenticated, IsHostelFeatureEnabled, CanManageOrWardenHostel]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["hostel", "student"]
    search_fields = ["visitor_name", "visitor_phone", "student__student_id"]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("hostel"), "hostel")
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("student"), "student"
        )
        serializer.save(institution=user.institution, recorded_by=user)
