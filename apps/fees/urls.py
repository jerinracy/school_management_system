"""URL configuration for Fee Management endpoints."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.fees.views import (
    AdvanceBalanceViewSet,
    DueListView,
    FeeHeadViewSet,
    FeeStructureViewSet,
    FineRuleViewSet,
    InvoiceViewSet,
    MoneyReceiptViewSet,
    PaymentViewSet,
    RefundViewSet,
    StudentFeeAssignmentViewSet,
    StudentWaiverViewSet,
    WaiverRuleViewSet,
)

app_name = "fees"

router = DefaultRouter()
router.register(r"heads", FeeHeadViewSet, basename="fee-head")
router.register(r"structures", FeeStructureViewSet, basename="fee-structure")
router.register(r"assignments", StudentFeeAssignmentViewSet, basename="fee-assignment")
router.register(r"waiver-rules", WaiverRuleViewSet, basename="waiver-rule")
router.register(r"student-waivers", StudentWaiverViewSet, basename="student-waiver")
router.register(r"fine-rules", FineRuleViewSet, basename="fine-rule")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"receipts", MoneyReceiptViewSet, basename="money-receipt")
router.register(r"advance-balances", AdvanceBalanceViewSet, basename="advance-balance")
router.register(r"refunds", RefundViewSet, basename="refund")

urlpatterns = [
    path("", include(router.urls)),
    path("due-list/", DueListView.as_view(), name="due-list"),
]
