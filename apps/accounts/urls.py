"""URL routing for authentication, profile, sessions, and RBAC."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    LogoutAllView,
    LogoutView,
    MeView,
    OTPRequestView,
    OTPVerifyView,
    PasswordChangeView,
    RoleViewSet,
    UserManagementViewSet,
    UserSessionViewSet,
)

app_name = "accounts"

router = DefaultRouter()
router.register(r"sessions", UserSessionViewSet, basename="session")
router.register(r"users", UserManagementViewSet, basename="user")
router.register(r"roles", RoleViewSet, basename="role")

urlpatterns = [
    # Core Auth Flows
    path("login/", LoginView.as_view(), name="login"),
    path("otp/request/", OTPRequestView.as_view(), name="otp_request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp_verify"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllView.as_view(), name="logout_all"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    # Current User Profile
    path("me/", MeView.as_view(), name="me"),
    # ViewSets (sessions, users, roles)
    path("", include(router.urls)),
]
