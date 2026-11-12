"""DRF ViewSets and GPS Ingestion endpoint for Transport Management."""

from typing import Any

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
)
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.mixins import TenantScopedMixin
from apps.students.models import Student
from apps.transport.models import (
    BoardingEvent,
    Driver,
    FuelLog,
    LiveLocation,
    Route,
    RouteStop,
    TransportAssignment,
    TransportFeeLink,
    TripLog,
    Vehicle,
    VehicleMaintenance,
)
from apps.transport.permissions import (
    CanManageTransport,
    CanOperateTripOrBoarding,
    CanReadTransportPortal,
    has_transport_staff_permission,
    resolve_driver_for_user,
    resolve_guardian_ward_ids,
    resolve_student_for_user,
)
from apps.transport.serializers import (
    BoardingEventSerializer,
    BoardingScanSerializer,
    DriverSerializer,
    FuelLogSerializer,
    GpsPingSerializer,
    GpsTokenRotateResponseSerializer,
    GpsTokenRotateSerializer,
    LiveLocationSerializer,
    RouteSerializer,
    RouteStopSerializer,
    TransportAssignmentSerializer,
    TransportFeeLinkSerializer,
    TripEndSerializer,
    TripLogSerializer,
    TripStartSerializer,
    VehicleMaintenanceSerializer,
    VehicleSerializer,
)
from apps.transport.services import (
    assign_transport,
    end_trip,
    ingest_gps_ping,
    record_boarding_event,
    rotate_vehicle_gps_token,
    start_trip,
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
    list=extend_schema(summary="List Vehicles"),
    retrieve=extend_schema(summary="Get Vehicle"),
    create=extend_schema(summary="Create Vehicle"),
    partial_update=extend_schema(summary="Update Vehicle"),
    destroy=extend_schema(summary="Delete Vehicle"),
)
class VehicleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related("branch").all()
    serializer_class = VehicleSerializer
    filterset_fields = ["branch", "vehicle_type", "status"]
    search_fields = ["registration_no", "make_model", "gps_device_id"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanManageTransport()]

    def get_queryset(self) -> QuerySet[Vehicle]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("branch"), "branch")
        super().perform_create(serializer)

    @extend_schema(
        summary="Rotate GPS Device Token for Vehicle",
        request=GpsTokenRotateSerializer,
        responses={200: GpsTokenRotateResponseSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="rotate-gps-token",
        permission_classes=[IsAuthenticated, CanManageTransport],
    )
    def rotate_gps_token(self, request: Request, pk: str | None = None) -> Response:
        vehicle = self.get_object()
        serializer = GpsTokenRotateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device_id = serializer.validated_data.get("gps_device_id") or vehicle.gps_device_id
        if not device_id:
            raise DRFValidationError({"gps_device_id": "Provide a gps_device_id."})
        raw_token = rotate_vehicle_gps_token(vehicle=vehicle, gps_device_id=device_id)
        return Response(
            {
                "vehicle_id": vehicle.id,
                "gps_device_id": vehicle.gps_device_id,
                "gps_token": raw_token,
            }
        )


@extend_schema_view(
    list=extend_schema(summary="List Drivers"),
    retrieve=extend_schema(summary="Get Driver"),
    create=extend_schema(summary="Create Driver"),
    partial_update=extend_schema(summary="Update Driver"),
    destroy=extend_schema(summary="Delete Driver"),
)
class DriverViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.select_related("staff").all()
    serializer_class = DriverSerializer
    filterset_fields = ["status"]
    search_fields = ["license_no", "staff__full_name_en", "staff__employee_id"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanManageTransport()]

    def get_queryset(self) -> QuerySet[Driver]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("staff"), "staff")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Transport Routes"),
    retrieve=extend_schema(summary="Get Transport Route"),
    create=extend_schema(summary="Create Transport Route"),
    partial_update=extend_schema(summary="Update Transport Route"),
    destroy=extend_schema(summary="Delete Transport Route"),
)
class RouteViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = (
        Route.objects.select_related("branch", "vehicle", "driver").prefetch_related("stops").all()
    )
    serializer_class = RouteSerializer
    filterset_fields = ["branch", "is_active", "vehicle", "driver"]
    search_fields = ["name", "code"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanManageTransport()]

    def get_queryset(self) -> QuerySet[Route]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("branch"), "branch")
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("vehicle"), "vehicle"
        )
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("driver"), "driver")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Route Stops"),
    retrieve=extend_schema(summary="Get Route Stop"),
    create=extend_schema(summary="Create Route Stop"),
    partial_update=extend_schema(summary="Update Route Stop"),
    destroy=extend_schema(summary="Delete Route Stop"),
)
class RouteStopViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = RouteStop.objects.select_related("route").all()
    serializer_class = RouteStopSerializer
    filterset_fields = ["route"]
    search_fields = ["name", "route__code"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanManageTransport()]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("route"), "route")
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Transport Fee Links"),
    retrieve=extend_schema(summary="Get Transport Fee Link"),
    create=extend_schema(summary="Create Transport Fee Link"),
    partial_update=extend_schema(summary="Update Transport Fee Link"),
    destroy=extend_schema(summary="Delete Transport Fee Link"),
)
class TransportFeeLinkViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = TransportFeeLink.objects.select_related("fee_head", "route", "session").all()
    serializer_class = TransportFeeLinkSerializer
    permission_classes = [IsAuthenticated, CanManageTransport]
    filterset_fields = ["route", "session", "fee_head"]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("fee_head"), "fee_head"
        )
        _ensure_same_tenant(user.institution_id, serializer.validated_data.get("route"), "route")
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("session"), "session"
        )
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Transport Assignments"),
    retrieve=extend_schema(summary="Get Transport Assignment"),
    create=extend_schema(summary="Assign Student or Staff to Route"),
    partial_update=extend_schema(summary="Update Transport Assignment"),
    destroy=extend_schema(summary="Delete Transport Assignment"),
)
class TransportAssignmentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = TransportAssignment.objects.select_related(
        "session", "route", "stop", "student", "staff", "transport_fee_link"
    ).all()
    serializer_class = TransportAssignmentSerializer
    filterset_fields = ["session", "route", "stop", "assignee_type", "is_active"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanManageTransport()]

    def get_queryset(self) -> QuerySet[TransportAssignment]:
        qs = super().get_queryset().filter(is_deleted=False)
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_transport_staff_permission(self.request, self):
            return qs
        student_ids = _visible_student_ids_for_user(user)
        if student_ids:
            return qs.filter(student_id__in=student_ids)
        return qs.none()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _ensure_same_tenant(user.institution_id, data.get("session"), "session")
        _ensure_same_tenant(user.institution_id, data.get("route"), "route")
        _ensure_same_tenant(user.institution_id, data.get("stop"), "stop")
        _ensure_same_tenant(user.institution_id, data.get("student"), "student")
        _ensure_same_tenant(user.institution_id, data.get("staff"), "staff")
        _ensure_same_tenant(
            user.institution_id, data.get("transport_fee_link"), "transport_fee_link"
        )
        try:
            assignment = assign_transport(
                institution=user.institution,
                session=data["session"],
                route=data["route"],
                stop=data["stop"],
                student=data.get("student"),
                staff=data.get("staff"),
                transport_fee_link=data.get("transport_fee_link"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(self.get_serializer(assignment).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(summary="List Vehicle Maintenance Logs"),
    retrieve=extend_schema(summary="Get Vehicle Maintenance Log"),
    create=extend_schema(summary="Create Vehicle Maintenance Log"),
    partial_update=extend_schema(summary="Update Vehicle Maintenance Log"),
    destroy=extend_schema(summary="Delete Vehicle Maintenance Log"),
)
class VehicleMaintenanceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = VehicleMaintenance.objects.select_related("vehicle").all()
    serializer_class = VehicleMaintenanceSerializer
    permission_classes = [IsAuthenticated, CanManageTransport]
    filterset_fields = ["vehicle", "maintenance_date"]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("vehicle"), "vehicle"
        )
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Fuel Logs"),
    retrieve=extend_schema(summary="Get Fuel Log"),
    create=extend_schema(summary="Create Fuel Log"),
    partial_update=extend_schema(summary="Update Fuel Log"),
    destroy=extend_schema(summary="Delete Fuel Log"),
)
class FuelLogViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = FuelLog.objects.select_related("vehicle").all()
    serializer_class = FuelLogSerializer
    permission_classes = [IsAuthenticated, CanManageTransport]
    filterset_fields = ["vehicle"]

    def perform_create(self, serializer: Any) -> None:
        user = self.request.user
        assert isinstance(user, User)
        _ensure_same_tenant(
            user.institution_id, serializer.validated_data.get("vehicle"), "vehicle"
        )
        super().perform_create(serializer)


@extend_schema_view(
    list=extend_schema(summary="List Trip Logs"),
    retrieve=extend_schema(summary="Get Trip Log"),
)
class TripLogViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TripLog.objects.select_related("route", "vehicle", "driver").all()
    serializer_class = TripLogSerializer
    filterset_fields = ["route", "vehicle", "driver", "status", "trip_date", "direction"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanOperateTripOrBoarding()]

    def get_queryset(self) -> QuerySet[TripLog]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_transport_staff_permission(self.request, self):
            return qs
        driver = resolve_driver_for_user(user)
        if driver is not None:
            return qs.filter(driver=driver)
        student_ids = _visible_student_ids_for_user(user)
        if student_ids and user.institution_id:
            route_ids = TransportAssignment.objects.filter(
                institution_id=user.institution_id,
                student_id__in=student_ids,
                is_deleted=False,
                is_active=True,
            ).values_list("route_id", flat=True)
            return qs.filter(route_id__in=route_ids)
        return qs.none()

    @extend_schema(
        summary="Start a Transport Trip",
        request=TripStartSerializer,
        responses={201: TripLogSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanOperateTripOrBoarding],
    )
    def start(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = TripStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        route = Route.objects.filter(
            id=data["route"], institution=user.institution, is_deleted=False
        ).first()
        if route is None:
            raise DRFValidationError({"route": "Route not found in this institution."})
        vehicle = (
            Vehicle.objects.filter(
                id=data["vehicle"], institution=user.institution, is_deleted=False
            ).first()
            if data.get("vehicle")
            else None
        )
        driver = (
            Driver.objects.filter(
                id=data["driver"], institution=user.institution, is_deleted=False
            ).first()
            if data.get("driver")
            else None
        )
        is_manager = bool(user.is_superuser or CanManageTransport().has_permission(request, self))
        try:
            trip = start_trip(
                institution=user.institution,
                route=route,
                driver=driver,
                vehicle=vehicle,
                direction=data["direction"],
                notes=data.get("notes", ""),
                actor=user,
                enforce_driver_ownership=not is_manager,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(TripLogSerializer(trip).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="End an In-Progress Transport Trip",
        request=TripEndSerializer,
        responses={200: TripLogSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanOperateTripOrBoarding],
    )
    def end(self, request: Request, pk: str | None = None) -> Response:
        user = request.user
        assert isinstance(user, User)
        trip = self.get_object()
        serializer = TripEndSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_manager = bool(user.is_superuser or CanManageTransport().has_permission(request, self))
        try:
            updated = end_trip(
                institution=user.institution,
                trip=trip,
                notes=serializer.validated_data.get("notes", ""),
                actor=user,
                enforce_driver_ownership=not is_manager,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        return Response(TripLogSerializer(updated).data)


@extend_schema_view(
    list=extend_schema(summary="List Boarding Events"),
    retrieve=extend_schema(summary="Get Boarding Event"),
)
class BoardingEventViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = BoardingEvent.objects.select_related("trip", "trip__route", "student", "stop").all()
    serializer_class = BoardingEventSerializer
    filterset_fields = ["trip", "student", "event_type", "method"]

    def get_permissions(self) -> list[Any]:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanReadTransportPortal()]
        return [IsAuthenticated(), CanOperateTripOrBoarding()]

    def get_queryset(self) -> QuerySet[BoardingEvent]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_transport_staff_permission(self.request, self):
            return qs
        driver = resolve_driver_for_user(user)
        if driver is not None:
            return qs.filter(trip__driver=driver)
        student_ids = _visible_student_ids_for_user(user)
        if student_ids:
            return qs.filter(student_id__in=student_ids)
        return qs.none()

    @extend_schema(
        summary="Scan Student Boarding/Dropping Event (Idempotent)",
        request=BoardingScanSerializer,
        responses={200: BoardingEventSerializer, 201: BoardingEventSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanOperateTripOrBoarding],
    )
    def scan(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = BoardingScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trip = TripLog.objects.filter(id=data["trip"], institution=user.institution).first()
        if trip is None:
            raise DRFValidationError({"trip": "Trip not found in this institution."})
        student = Student.objects.filter(
            id=data["student"], institution=user.institution, is_deleted=False
        ).first()
        if student is None:
            raise DRFValidationError({"student": "Student not found in this institution."})
        stop = (
            RouteStop.objects.filter(id=data["stop"], institution=user.institution).first()
            if data.get("stop")
            else None
        )

        is_manager = bool(user.is_superuser or CanManageTransport().has_permission(request, self))
        if not is_manager:
            driver = resolve_driver_for_user(user)
            if driver is None or trip.driver_id != driver.id:
                raise PermissionDenied("Drivers may only record boarding on their own trips.")

        try:
            event, created = record_boarding_event(
                institution=user.institution,
                trip=trip,
                student=student,
                event_type=data["event_type"],
                stop=stop,
                method=data["method"],
                event_ts=data.get("event_ts"),
                idempotency_key=data.get("idempotency_key", ""),
                actor=user,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(BoardingEventSerializer(event).data, status=code)


@extend_schema_view(
    list=extend_schema(summary="List Live Location History"),
    retrieve=extend_schema(summary="Get Live Location Ping"),
)
class LiveLocationViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LiveLocation.objects.select_related("vehicle", "trip").all()
    serializer_class = LiveLocationSerializer
    permission_classes = [IsAuthenticated, CanReadTransportPortal]
    filterset_fields = ["vehicle", "trip"]

    def get_queryset(self) -> QuerySet[LiveLocation]:
        qs = super().get_queryset()
        user = self.request.user
        assert isinstance(user, User)
        if user.is_superuser or has_transport_staff_permission(self.request, self):
            return qs
        student_ids = _visible_student_ids_for_user(user)
        if student_ids and user.institution_id:
            vehicle_ids = (
                TransportAssignment.objects.filter(
                    institution_id=user.institution_id,
                    student_id__in=student_ids,
                    is_deleted=False,
                    is_active=True,
                    route__vehicle_id__isnull=False,
                )
                .values_list("route__vehicle_id", flat=True)
                .distinct()
            )
            return qs.filter(vehicle_id__in=vehicle_ids)
        return qs.none()

    @extend_schema(
        summary="Get Latest Live Location for a Vehicle",
        parameters=[OpenApiParameter("vehicle", str, required=True)],
        responses={200: LiveLocationSerializer},
    )
    @action(detail=False, methods=["get"])
    def latest(self, request: Request) -> Response:
        vehicle_id = request.query_params.get("vehicle")
        if not vehicle_id:
            raise DRFValidationError({"vehicle": "Query parameter 'vehicle' is required."})
        ping = self.get_queryset().filter(vehicle_id=vehicle_id).order_by("-recorded_at").first()
        if ping is None:
            return Response({"detail": "No location data found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(ping).data)


class GpsPingView(APIView):
    """Device-token-authenticated GPS ping ingestion endpoint."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Ingest Vehicle GPS Location Ping (Device Token Auth)",
        request=GpsPingSerializer,
        responses={201: LiveLocationSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = GpsPingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device_id = request.headers.get("X-GPS-Device-Id") or data.get("gps_device_id", "")
        raw_token = request.headers.get("X-GPS-Device-Token", "")
        if not raw_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                raw_token = auth_header[7:].strip()

        try:
            ping = ingest_gps_ping(
                gps_device_id=device_id,
                raw_token=raw_token,
                latitude=data["latitude"],
                longitude=data["longitude"],
                speed_kmh=data["speed_kmh"],
                recorded_at=data.get("recorded_at"),
            )
        except DjangoPermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(LiveLocationSerializer(ping).data, status=status.HTTP_201_CREATED)
