"""URL routing for Guardian and Family module."""

from rest_framework.routers import DefaultRouter

from apps.guardians.views import AuthorizedPickupViewSet, FamilyViewSet, GuardianViewSet

app_name = "guardians"

router = DefaultRouter()
router.register(r"guardians", GuardianViewSet, basename="guardian")
router.register(r"families", FamilyViewSet, basename="family")
router.register(r"pickups", AuthorizedPickupViewSet, basename="pickup")

urlpatterns = router.urls
