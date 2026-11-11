"""URL configuration for hardware devices, punches, enrollments, and webhooks."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.devices.views import (
    BiometricConsentViewSet,
    BiometricEnrollmentViewSet,
    DeviceCommandViewSet,
    DeviceGroupViewSet,
    DeviceUserMapViewSet,
    DeviceViewSet,
    GenericWebhookPushView,
    RawPunchViewSet,
    UnmappedPunchViewSet,
    ZKTecoCdataView,
    ZKTecoDeviceCmdView,
    ZKTecoGetRequestView,
)

app_name = "devices"

router = DefaultRouter()
router.register("terminals", DeviceViewSet, basename="terminal")
router.register("groups", DeviceGroupViewSet, basename="group")
router.register("user-maps", DeviceUserMapViewSet, basename="user-map")
router.register("consents", BiometricConsentViewSet, basename="consent")
router.register("enrollments", BiometricEnrollmentViewSet, basename="enrollment")
router.register("commands", DeviceCommandViewSet, basename="command")
router.register("punches", RawPunchViewSet, basename="punch")
router.register("unmapped-punches", UnmappedPunchViewSet, basename="unmapped-punch")

urlpatterns = [
    path("", include(router.urls)),
    path("push/webhook/", GenericWebhookPushView.as_view(), name="generic-webhook"),
    # Namespaced aliases for ADMS testing
    path("iclock/cdata", ZKTecoCdataView.as_view(), name="adms-cdata"),
    path("iclock/getrequest", ZKTecoGetRequestView.as_view(), name="adms-getrequest"),
    path("iclock/devicecmd", ZKTecoDeviceCmdView.as_view(), name="adms-devicecmd"),
]
