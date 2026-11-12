"""URL routing for Library Management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.library.views import (
    BookCopyViewSet,
    BookIssueViewSet,
    BookViewSet,
    EBookViewSet,
    LibraryFineViewSet,
    LibraryMemberViewSet,
    LibraryPolicyViewSet,
    ReservationViewSet,
)

app_name = "library"

router = DefaultRouter()
router.register("policies", LibraryPolicyViewSet, basename="policy")
router.register("books", BookViewSet, basename="book")
router.register("copies", BookCopyViewSet, basename="copy")
router.register("members", LibraryMemberViewSet, basename="member")
router.register("issues", BookIssueViewSet, basename="issue")
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("fines", LibraryFineViewSet, basename="fine")
router.register("ebooks", EBookViewSet, basename="ebook")

urlpatterns = [
    path("", include(router.urls)),
]
