"""URL routing for Transport Management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.transport.views import (
    BoardingEventViewSet,
    DriverViewSet,
    FuelLogViewSet,
    GpsPingView,
    LiveLocationViewSet,
    RouteStopViewSet,
    RouteViewSet,
    TransportAssignmentViewSet,
    TransportFeeLinkViewSet,
    TripLogViewSet,
    VehicleMaintenanceViewSet,
    VehicleViewSet,
)

app_name = "transport"

router = DefaultRouter()
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("drivers", DriverViewSet, basename="driver")
router.register("routes", RouteViewSet, basename="route")
router.register("stops", RouteStopViewSet, basename="stop")
router.register("fee-links", TransportFeeLinkViewSet, basename="fee-link")
router.register("assignments", TransportAssignmentViewSet, basename="assignment")
router.register("maintenances", VehicleMaintenanceViewSet, basename="maintenance")
router.register("fuel-logs", FuelLogViewSet, basename="fuel-log")
router.register("trips", TripLogViewSet, basename="trip")
router.register("boarding-events", BoardingEventViewSet, basename="boarding-event")
router.register("live-locations", LiveLocationViewSet, basename="live-location")

urlpatterns = [
    path("gps/ping/", GpsPingView.as_view(), name="gps-ping"),
    path("", include(router.urls)),
]
