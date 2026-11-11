"""URL configuration for Students app."""

from rest_framework.routers import DefaultRouter

from apps.students.views import (
    PromotionViewSet,
    StudentEnrollmentViewSet,
    StudentViewSet,
    TestimonialViewSet,
    TransferCertificateViewSet,
)

app_name = "students"

router = DefaultRouter()
router.register(r"enrollments", StudentEnrollmentViewSet, basename="enrollments")
router.register(r"promotions", PromotionViewSet, basename="promotions")
router.register(
    r"transfer-certificates", TransferCertificateViewSet, basename="transfer-certificates"
)
router.register(r"testimonials", TestimonialViewSet, basename="testimonials")
router.register(r"", StudentViewSet, basename="students")

urlpatterns = router.urls
