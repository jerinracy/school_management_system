"""URL routing for Staff, HR, and Leave module."""

from rest_framework.routers import DefaultRouter

from apps.staff.views import (
    DepartmentViewSet,
    DesignationViewSet,
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
    StaffViewSet,
    TeacherAssignmentViewSet,
)

app_name = "staff"

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"designations", DesignationViewSet, basename="designation")
router.register(r"staff", StaffViewSet, basename="staff")
router.register(r"leave-types", LeaveTypeViewSet, basename="leave-type")
router.register(r"leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register(r"leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register(r"teacher-assignments", TeacherAssignmentViewSet, basename="teacher-assignment")

urlpatterns = router.urls
