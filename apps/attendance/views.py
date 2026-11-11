"""API ViewSets for attendance policies, daily records, period tracking, corrections, and mobile check-ins."""

from datetime import date
from typing import Any, cast

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from apps.academics.models import RoutineSlot, Section, Subject
from apps.accounts.models import User
from apps.attendance.models import (
    AttendanceCorrection,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceSource,
    AttendanceStatus,
    DailyAttendance,
    MobileCheckin,
    PeriodAttendance,
    PolicyAssignment,
    PunchDirection,
)
from apps.attendance.permissions import (
    CanApproveCorrection,
    CanManageAttendance,
    CanTakePeriodAttendance,
    CanViewAttendance,
)
from apps.attendance.serializers import (
    AttendanceCorrectionCreateSerializer,
    AttendanceCorrectionDecideSerializer,
    AttendanceCorrectionSerializer,
    AttendanceEventSerializer,
    AttendancePolicySerializer,
    BulkManualAttendanceSerializer,
    DailyAttendanceSerializer,
    MobileCheckinCreateSerializer,
    MobileCheckinSerializer,
    PeriodAttendanceBulkSubmitSerializer,
    PeriodAttendanceSerializer,
    PolicyAssignmentSerializer,
    PolicySimulateRequestSerializer,
    PolicySimulateResultSerializer,
    RecomputeAttendanceRequestSerializer,
)
from apps.attendance.services import (
    decide_attendance_correction,
    evaluate_daily_status,
    recompute_daily_attendance,
    request_attendance_correction,
    resolve_effective_policy,
    submit_manual_attendance,
    update_daily_attendance_for_person,
    validate_geofence,
)
from apps.core.mixins import TenantScopedMixin
from apps.institutions.models import Institution
from apps.students.models import Student


def _get_request_institution(request: Request) -> Institution:
    user = request.user
    if not hasattr(user, "institution") or user.institution is None:
        raise PermissionDenied("User is not associated with an institution.")
    return user.institution


class AttendancePolicyViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Manage institutional attendance policies and simulate outcomes."""

    queryset = AttendancePolicy.objects.select_related("branch", "shift", "class_level").filter(
        is_deleted=False
    )
    serializer_class = AttendancePolicySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["user_type", "branch", "shift", "class_level", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "version", "effective_from"]
    ordering = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve", "simulate"]:
            return [permissions.IsAuthenticated(), (CanViewAttendance | CanManageAttendance)()]
        return [permissions.IsAuthenticated(), CanManageAttendance()]

    @action(detail=True, methods=["post"], url_path="simulate")
    def simulate(self, request: Request, pk: Any = None) -> Response:
        """Dry-run policy evaluation on sample punch timestamps."""
        policy = self.get_object()
        req_serializer = PolicySimulateRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        data = req_serializer.validated_data

        eval_result = evaluate_daily_status(
            events=data["punches"],
            policy=policy,
            target_date=data["target_date"],
            is_holiday=data.get("is_holiday", False),
            is_weekend=data.get("is_weekend", False),
            has_approved_leave=data.get("has_approved_leave", False),
        )

        res_data = {
            "status": eval_result.status,
            "first_in": eval_result.first_in,
            "last_out": eval_result.last_out,
            "total_minutes": eval_result.total_minutes,
            "minutes_late": eval_result.minutes_late,
            "minutes_early_leave": eval_result.minutes_early_leave,
            "remarks": eval_result.remarks,
        }
        return Response(PolicySimulateResultSerializer(res_data).data)


class PolicyAssignmentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Scoped binding of attendance policies to branches, shifts, and classes."""

    queryset = PolicyAssignment.objects.select_related(
        "policy", "branch", "shift", "class_level", "section"
    ).all()
    serializer_class = PolicyAssignmentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["user_type", "branch", "shift", "class_level", "section"]
    ordering = ["-priority", "-created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewAttendance | CanManageAttendance)()]
        return [permissions.IsAuthenticated(), CanManageAttendance()]


class DailyAttendanceViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Daily aggregated attendance records for students and staff."""

    queryset = DailyAttendance.objects.select_related("student", "staff", "policy").filter(
        is_deleted=False
    )
    serializer_class = DailyAttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["date", "user_type", "status", "is_overridden"]
    search_fields = [
        "student__name_en",
        "student__student_id",
        "staff__full_name_en",
        "staff__employee_id",
    ]
    ordering_fields = ["date", "first_in", "minutes_late", "total_minutes"]
    ordering = ["-date"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve", "staff_summary"]:
            return [permissions.IsAuthenticated(), (CanViewAttendance | CanManageAttendance)()]
        return [permissions.IsAuthenticated(), CanManageAttendance()]

    @action(detail=False, methods=["post"], url_path="bulk-manual")
    def bulk_manual(self, request: Request) -> Response:
        """Manual bulk roll call submission by section or department."""
        institution = _get_request_institution(request)
        serializer = BulkManualAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        records = submit_manual_attendance(
            institution=institution,
            target_date=data["date"],
            user_type=data["user_type"],
            records=data["records"],
            taken_by=request.user,
        )
        return Response(
            {
                "message": f"Successfully updated manual attendance for {len(records)} persons.",
                "count": len(records),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="recompute")
    def recompute(self, request: Request) -> Response:
        """Idempotently recompute daily attendance across a date range."""
        institution = _get_request_institution(request)
        serializer = RecomputeAttendanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        count = recompute_daily_attendance(
            institution=institution,
            start_date=data["start_date"],
            end_date=data["end_date"],
            user_type=data.get("user_type", "all"),
            student_ids=data.get("student_ids"),
            staff_ids=data.get("staff_ids"),
        )
        return Response(
            {
                "message": f"Successfully recomputed {count} daily attendance records.",
                "recomputed_count": count,
            }
        )

    @action(detail=False, methods=["get"], url_path="staff-summary")
    def staff_summary(self, request: Request) -> Response:
        """Aggregated staff attendance metrics for HR and payroll."""
        institution = _get_request_institution(request)
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        today = timezone.now().date()
        start_date = date.fromisoformat(start_date_str) if start_date_str else today.replace(day=1)
        end_date = date.fromisoformat(end_date_str) if end_date_str else today

        qs = (
            DailyAttendance.objects.filter(
                institution=institution,
                user_type="staff",
                date__gte=start_date,
                date__lte=end_date,
                is_deleted=False,
            )
            .values("staff_id", "staff__full_name_en", "staff__employee_id")
            .annotate(
                total_days=Count("id"),
                present_days=Count("id", filter=Q(status=AttendanceStatus.PRESENT)),
                late_days=Count("id", filter=Q(status=AttendanceStatus.LATE)),
                half_days=Count("id", filter=Q(status=AttendanceStatus.HALF_DAY)),
                absent_days=Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
                leave_days=Count("id", filter=Q(status=AttendanceStatus.LEAVE)),
                total_work_minutes=Sum("total_minutes"),
                total_late_minutes=Sum("minutes_late"),
            )
            .order_by("staff__full_name_en")
        )

        return Response(list(qs))


class PeriodAttendanceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Subject and period-level classroom roll call."""

    queryset = PeriodAttendance.objects.select_related(
        "section", "routine_slot", "subject", "teacher", "student"
    ).filter(is_deleted=False)
    serializer_class = PeriodAttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["date", "section", "subject", "teacher", "status"]
    search_fields = ["student__name_en", "remarks"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewAttendance | CanTakePeriodAttendance)()]
        return [permissions.IsAuthenticated(), (CanTakePeriodAttendance | CanManageAttendance)()]

    @action(detail=False, methods=["post"], url_path="bulk-submit")
    def bulk_submit(self, request: Request) -> Response:
        """Bulk submission of subject period attendance by teacher."""
        institution = _get_request_institution(request)
        serializer = PeriodAttendanceBulkSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        section = get_object_or_404(Section, id=data["section_id"], institution=institution)
        subject = get_object_or_404(Subject, id=data["subject_id"], institution=institution)
        slot = None
        if data.get("routine_slot_id"):
            slot = get_object_or_404(RoutineSlot, id=data["routine_slot_id"], section=section)

        staff_teacher = getattr(request.user, "staff_profile", None)

        created_count = 0
        with timezone.override(timezone.get_current_timezone()):
            for item in data["records"]:
                student = get_object_or_404(Student, id=item["student_id"], institution=institution)
                PeriodAttendance.objects.update_or_create(
                    institution=institution,
                    date=data["date"],
                    section=section,
                    routine_slot=slot,
                    subject=subject,
                    student=student,
                    defaults={
                        "teacher": staff_teacher,
                        "status": item["status"],
                        "remarks": item.get("remarks", ""),
                    },
                )
                created_count += 1

        return Response(
            {"message": f"Successfully saved {created_count} student period attendance records."},
            status=status.HTTP_200_OK,
        )


class AttendanceCorrectionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Attendance rectification requests and manager approval chain."""

    queryset = AttendanceCorrection.objects.select_related(
        "daily_attendance", "requested_by", "approved_by"
    ).all()
    serializer_class = AttendanceCorrectionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["approval_status"]
    ordering = ["-created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve", "create"]:
            return [permissions.IsAuthenticated(), (CanViewAttendance | CanManageAttendance)()]
        return [permissions.IsAuthenticated(), (CanApproveCorrection | CanManageAttendance)()]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        institution = _get_request_institution(request)
        serializer = AttendanceCorrectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        daily = get_object_or_404(
            DailyAttendance, id=data["daily_attendance_id"], institution=institution
        )
        correction = request_attendance_correction(
            daily_attendance=daily,
            requested_by=request.user,
            reason=data["reason"],
            status_after=data["status_after"],
            time_in_after=data.get("time_in_after"),
            time_out_after=data.get("time_out_after"),
        )
        return Response(
            AttendanceCorrectionSerializer(correction).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request: Request, pk: Any = None) -> Response:
        """Approve or reject attendance correction."""
        correction = self.get_object()
        serializer = AttendanceCorrectionDecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        decided = decide_attendance_correction(
            correction=correction,
            approver=request.user,
            approved=data["approved"],
            rejection_reason=data.get("rejection_reason", ""),
        )
        return Response(AttendanceCorrectionSerializer(decided).data)


class AttendanceEventViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only audit stream of normalized attendance check-in/out events."""

    queryset = AttendanceEvent.objects.select_related("student", "staff", "device").all()
    serializer_class = AttendanceEventSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["user_type", "direction", "source", "method"]
    search_fields = ["student__name_en", "staff__full_name_en"]
    ordering = ["-timestamp"]
    permission_classes = [permissions.IsAuthenticated, CanViewAttendance | CanManageAttendance]


class MobileCheckinViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Mobile app GPS-validated check-in intake."""

    queryset = MobileCheckin.objects.select_related("user", "staff").all()
    serializer_class = MobileCheckinSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["is_within_geofence"]
    ordering = ["-timestamp"]
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="checkin")
    def checkin(self, request: Request) -> Response:
        """Validate GPS coordinates and register mobile check-in event."""
        institution = _get_request_institution(request)
        serializer = MobileCheckinCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        staff_member = getattr(request.user, "staff_profile", None)
        user_type = "staff" if staff_member else "student"
        now = data.get("timestamp") or timezone.now()

        # Resolve campus geofence coordinates from policy or branch
        policy = resolve_effective_policy(
            institution=institution,
            user_type=user_type,
            target_date=now.date(),
        )

        center_lat = policy.geofence_latitude
        center_lon = policy.geofence_longitude
        allowed_radius = policy.geofence_radius_meters

        if (
            (center_lat is None or center_lon is None)
            and staff_member
            and staff_member.institution.branches.exists()
        ):
            branch = staff_member.institution.branches.filter(latitude__isnull=False).first()
            if branch:
                center_lat = branch.latitude
                center_lon = branch.longitude
                allowed_radius = branch.geofence_radius_meters

        is_valid, dist_meters = validate_geofence(
            user_lat=data["latitude"],
            user_lon=data["longitude"],
            center_lat=center_lat,
            center_lon=center_lon,
            allowed_radius_meters=allowed_radius,
        )

        # Create AttendanceEvent if valid
        event = None
        if is_valid:
            event = AttendanceEvent.objects.create(
                institution=institution,
                user_type=user_type,
                staff=staff_member,
                direction=PunchDirection.AUTO,
                method="mobile",
                timestamp=now,
                source=AttendanceSource.MOBILE,
                is_processed=True,
            )
            # Recompute daily record
            if staff_member:
                update_daily_attendance_for_person(
                    institution=institution,
                    user_type="staff",
                    person_id=staff_member.id,
                    target_date=now.date(),
                )

        checkin_log = MobileCheckin.objects.create(
            institution=institution,
            user=cast(User, request.user),
            staff=staff_member,
            latitude=data["latitude"],
            longitude=data["longitude"],
            accuracy_meters=data.get("accuracy_meters", 10.0),
            is_within_geofence=is_valid,
            geofence_distance_meters=dist_meters,
            selfie_image=data.get("selfie_image"),
            device_info=data.get("device_info", ""),
            timestamp=now,
            attendance_event=event,
        )

        resp_status = status.HTTP_201_CREATED if is_valid else status.HTTP_400_BAD_REQUEST
        return Response(
            {
                "status": "success" if is_valid else "rejected",
                "is_within_geofence": is_valid,
                "distance_meters": dist_meters,
                "allowed_radius_meters": allowed_radius,
                "checkin_id": str(checkin_log.id),
                "event_id": str(event.id) if event else None,
            },
            status=resp_status,
        )
