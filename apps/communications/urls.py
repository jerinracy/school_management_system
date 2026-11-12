"""URL routing for communications module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.communications.views import (
    ChatThreadViewSet,
    DeviceTokenViewSet,
    EmergencyAlertViewSet,
    NoticeViewSet,
    NotificationDeliveryViewSet,
    NotificationPreferenceView,
    NotificationTemplateViewSet,
    SMSGatewayConfigViewSet,
)

app_name = "communications"

router = DefaultRouter()
router.register(r"gateways", SMSGatewayConfigViewSet, basename="gateway")
router.register(r"templates", NotificationTemplateViewSet, basename="template")
router.register(r"deliveries", NotificationDeliveryViewSet, basename="delivery")
router.register(r"device-tokens", DeviceTokenViewSet, basename="device-token")
router.register(r"notices", NoticeViewSet, basename="notice")
router.register(r"chat/threads", ChatThreadViewSet, basename="chat-thread")
router.register(r"emergency-alerts", EmergencyAlertViewSet, basename="emergency-alert")

urlpatterns = [
    path(
        "preferences/me/", NotificationPreferenceView.as_view(), name="notification_preference_me"
    ),
    path("", include(router.urls)),
]
