"""API ViewSets for Staff, HR, Leave, and Teacher Assignments."""

from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import TenantScopedMixin
from apps.institutions.models import AcademicSession, Institution
from apps.staff.models import (
    Department,
    Designation,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Staff,
    TeacherAssignment,
)
from apps.staff.permissions import (
    CanApplyLeave,
    CanApproveLeave,
    CanManageStaff,
    CanViewStaff,
    IsSelfStaff,
)
from apps.staff.selectors import get_teacher_workload_summary
from apps.staff.serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    LeaveApplyActionSerializer,
    LeaveBalanceSerializer,
    LeaveDecideActionSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    StaffCreateUpdateSerializer,
    StaffDetailSerializer,
    StaffListSerializer,
    TeacherAssignmentSerializer,
    WorkloadSummarySerializer,
)
from apps.staff.services import (
    apply_for_leave,
    approve_leave,
    cancel_leave,
    create_portal_user_for_staff,
    generate_employee_id,
    initialize_leave_balances_for_session,
    recommend_leave,
    reject_leave,
)


def _get_request_institution(request: Request) -> Institution:
    user = request.user
    if not hasattr(user, "institution") or user.institution is None:
        raise ValidationError("User has no associated institution.")
    return user.institution


def _get_request_staff(request: Request) -> Staff | None:
    user = request.user
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "staff_profile", None)


class DepartmentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Department master data endpoints."""

    queryset = Department.objects.select_related("head_of_department").all()
    serializer_class = DepartmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewStaff | CanManageStaff)()]
        return [permissions.IsAuthenticated(), CanManageStaff()]


class DesignationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Designation hierarchy master data endpoints."""

    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "title_bn", "code"]
    filterset_fields = ["role_category"]
    ordering_fields = ["rank_order", "title"]
    ordering = ["rank_order", "title"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewStaff | CanManageStaff)()]
        return [permissions.IsAuthenticated(), CanManageStaff()]


class StaffViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Comprehensive employee lifecycle management endpoints."""

    queryset = Staff.objects.select_related("department", "designation", "user").prefetch_related(
        "educations", "documents", "id_cards"
    )
    serializer_class = StaffCreateUpdateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "full_name_en",
        "full_name_bn",
        "employee_id",
        "phone",
        "nid",
        "mpo_index_number",
    ]
    filterset_fields = ["staff_type", "status", "department", "designation", "is_mpo", "gender"]
    ordering_fields = ["employee_id", "full_name_en", "joining_date", "created_at"]
    ordering = ["designation__rank_order", "full_name_en"]

    def get_serializer_class(self) -> type[Any]:
        if self.action == "list":
            return StaffListSerializer
        if self.action == "retrieve":
            return StaffDetailSerializer
        return StaffCreateUpdateSerializer

    def get_permissions(self) -> list[Any]:
        if self.action in ["me", "workload"]:
            return [permissions.IsAuthenticated()]
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewStaff | CanManageStaff)()]
        return [permissions.IsAuthenticated(), CanManageStaff()]

    def perform_create(self, serializer: Any) -> None:
        inst = _get_request_institution(self.request)
        emp_id = serializer.validated_data.get("employee_id")
        if not emp_id:
            emp_id = generate_employee_id(inst)
        serializer.save(institution=inst, employee_id=emp_id)

    @extend_schema(responses={200: StaffDetailSerializer})
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        """Retrieve profile of the currently authenticated staff member."""
        staff = _get_request_staff(request)
        if not staff:
            raise ValidationError("Authenticated user is not linked to an active staff profile.")
        return Response(StaffDetailSerializer(staff).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: WorkloadSummarySerializer})
    @action(detail=True, methods=["get"], url_path="workload")
    def workload(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve weekly teaching schedule and curriculum workload metrics for a teacher."""
        teacher = self.get_object()
        session_id = request.query_params.get("session_id")
        session = None
        if session_id:
            session = AcademicSession.objects.filter(
                id=session_id, institution=_get_request_institution(request)
            ).first()

        metrics = get_teacher_workload_summary(teacher, session)
        return Response(metrics, status=status.HTTP_200_OK)

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["post"], url_path="create-portal-account")
    def create_portal_account(self, request: Request, pk: str | None = None) -> Response:
        """Provision or reset portal access credentials for this staff member."""
        staff = self.get_object()
        user, _ = create_portal_user_for_staff(staff)
        return Response(
            {
                "detail": "Staff portal account provisioned and credentials sent via SMS.",
                "user_id": str(user.id),
                "phone": staff.phone,
            },
            status=status.HTTP_200_OK,
        )


class LeaveTypeViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Institutional leave policy categories."""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code"]
    ordering = ["name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewStaff | CanManageStaff)()]
        return [permissions.IsAuthenticated(), CanManageStaff()]


class LeaveBalanceViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Employee annual leave quota and usage balances."""

    queryset = LeaveBalance.objects.select_related("staff", "leave_type", "session").all()
    serializer_class = LeaveBalanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["staff", "leave_type", "session"]
    ordering = ["staff__full_name_en", "leave_type__name"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [
                permissions.IsAuthenticated(),
                (CanViewStaff | CanManageStaff | IsSelfStaff)(),
            ]
        return [permissions.IsAuthenticated(), CanManageStaff()]

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["post"], url_path="initialize-session")
    def initialize_session(self, request: Request) -> Response:
        """Initialize standard annual leave balances for all active staff for a specified session."""
        session_id = request.data.get("session_id")
        if not session_id:
            raise ValidationError({"session_id": "Valid academic session required."})
        inst = _get_request_institution(request)
        session = AcademicSession.objects.filter(id=str(session_id), institution=inst).first()
        if not session:
            raise ValidationError({"session_id": "Valid academic session required."})

        count = initialize_leave_balances_for_session(inst, session)
        return Response(
            {"detail": f"Successfully initialized {count} leave balance ledgers."},
            status=status.HTTP_200_OK,
        )


class LeaveRequestViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Leave application submission and multi-tier approval workflow."""

    queryset = LeaveRequest.objects.select_related(
        "staff", "leave_type", "session", "recommender", "approver"
    ).all()
    serializer_class = LeaveRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["staff", "leave_type", "session", "status"]
    ordering = ["-start_date", "-created_at"]

    def get_permissions(self) -> list[Any]:
        if self.action == "create":
            return [permissions.IsAuthenticated(), (CanApplyLeave | CanManageStaff)()]
        if self.action in ["list", "retrieve"]:
            return [
                permissions.IsAuthenticated(),
                (CanViewStaff | CanManageStaff | IsSelfStaff)(),
            ]
        if self.action in ["recommend", "approve", "reject"]:
            return [permissions.IsAuthenticated(), (CanApproveLeave | CanManageStaff)()]
        if self.action == "cancel":
            return [permissions.IsAuthenticated(), (CanManageStaff | IsSelfStaff)()]
        return [permissions.IsAuthenticated(), CanManageStaff()]

    @extend_schema(request=LeaveApplyActionSerializer, responses={201: LeaveRequestSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Submit a new leave application with date validation and balance deduction."""
        serializer = LeaveApplyActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        inst = _get_request_institution(request)

        staff_id = data.get("staff_id")
        if staff_id:
            staff = Staff.objects.filter(id=staff_id, institution=inst).first()
        else:
            staff = _get_request_staff(request)

        if not staff:
            raise ValidationError({"staff_id": "Staff profile not resolved for this request."})

        leave_type = LeaveType.objects.filter(id=data["leave_type_id"], institution=inst).first()
        if not leave_type:
            raise ValidationError({"leave_type_id": "Leave type not found."})

        session = AcademicSession.objects.filter(id=data["session_id"], institution=inst).first()
        if not session:
            raise ValidationError({"session_id": "Academic session not found."})

        leave_req = apply_for_leave(
            staff=staff,
            leave_type=leave_type,
            session=session,
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            emergency_phone=data.get("emergency_phone", ""),
            attachment=data.get("attachment"),
        )
        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=LeaveDecideActionSerializer, responses={200: LeaveRequestSerializer})
    @action(detail=True, methods=["post"], url_path="recommend")
    def recommend(self, request: Request, pk: str | None = None) -> Response:
        """HOD stage: Recommend leave application for final executive approval."""
        leave_req = self.get_object()
        reviewer_staff = _get_request_staff(request)
        if not reviewer_staff:
            raise PermissionDenied("Only staff members can recommend leave applications.")

        updated = recommend_leave(leave_req, reviewer_staff)
        return Response(LeaveRequestSerializer(updated).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: LeaveRequestSerializer})
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """Executive stage: Grant final leave approval and deduct from used days."""
        leave_req = self.get_object()
        approver_staff = _get_request_staff(request)
        if not approver_staff:
            approver_staff = Staff.objects.filter(
                institution=_get_request_institution(request)
            ).first()
            if not approver_staff:
                raise PermissionDenied("No authoritative staff profile found to approve leave.")

        updated = approve_leave(leave_req, approver_staff)
        return Response(LeaveRequestSerializer(updated).data, status=status.HTTP_200_OK)

    @extend_schema(request=LeaveDecideActionSerializer, responses={200: LeaveRequestSerializer})
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request: Request, pk: str | None = None) -> Response:
        """Decline leave request and release reserved pending days back to balance."""
        leave_req = self.get_object()
        serializer = LeaveDecideActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        decider_staff = (
            _get_request_staff(request)
            or Staff.objects.filter(institution=_get_request_institution(request)).first()
        )
        if not decider_staff:
            raise PermissionDenied("No authoritative staff profile found.")

        updated = reject_leave(leave_req, decider_staff, reason)
        return Response(LeaveRequestSerializer(updated).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: LeaveRequestSerializer})
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Cancel an application and restore days to balance ledger."""
        leave_req = self.get_object()
        updated = cancel_leave(leave_req)
        return Response(LeaveRequestSerializer(updated).data, status=status.HTTP_200_OK)


class TeacherAssignmentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Teacher curriculum assignments to classes, sections, and subjects."""

    queryset = TeacherAssignment.objects.select_related(
        "teacher", "subject", "section__class_level", "session"
    ).all()
    serializer_class = TeacherAssignmentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["teacher", "subject", "section", "session", "is_primary_teacher"]
    ordering = ["section", "subject"]

    def get_permissions(self) -> list[Any]:
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), (CanViewStaff | CanManageStaff)()]
        return [permissions.IsAuthenticated(), CanManageStaff()]
