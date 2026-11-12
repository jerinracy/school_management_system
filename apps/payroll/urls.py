"""URL routing for the Payroll Management API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payroll.views import (
    PayrollRunViewSet,
    PayslipViewSet,
    SalaryComponentViewSet,
    SalaryStructureLineViewSet,
    SalaryStructureViewSet,
    StaffLoanViewSet,
    StaffSalaryOverrideViewSet,
    StaffSalaryProfileViewSet,
)

app_name = "payroll"

router = DefaultRouter()
router.register("components", SalaryComponentViewSet, basename="component")
router.register("structures", SalaryStructureViewSet, basename="structure")
router.register("structure-lines", SalaryStructureLineViewSet, basename="structure-line")
router.register("profiles", StaffSalaryProfileViewSet, basename="profile")
router.register("overrides", StaffSalaryOverrideViewSet, basename="override")
router.register("loans", StaffLoanViewSet, basename="loan")
router.register("runs", PayrollRunViewSet, basename="run")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = [
    path("", include(router.urls)),
]
