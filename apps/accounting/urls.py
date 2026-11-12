"""Accounting module URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounting.views import (
    AccountViewSet,
    CashbookView,
    FinancialReportsViewSet,
    FiscalYearViewSet,
    JournalEntryViewSet,
)

app_name = "accounting"

router = DefaultRouter()
router.register(r"fiscal-years", FiscalYearViewSet, basename="fiscal-year")
router.register(r"accounts", AccountViewSet, basename="account")
router.register(r"vouchers", JournalEntryViewSet, basename="voucher")
router.register(r"reports", FinancialReportsViewSet, basename="financial-report")

urlpatterns = [
    path("cashbook/", CashbookView.as_view(), name="cashbook"),
    path("", include(router.urls)),
]
