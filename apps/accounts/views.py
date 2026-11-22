"""DRF Views and ViewSets for Authentication, Identity, and RBAC."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.mixins import TenantScopedMixin
from apps.core.utils.phone import normalize_bd_phone, validate_bd_phone

from .models import Role, User, UserRole, UserSession
from .permissions import HasModulePermission
from .serializers import (
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordChangeSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserProfileUpdateSerializer,
    UserRoleSerializer,
    UserSerializer,
    UserSessionSerializer,
)
from .services.auth import (
    generate_phone_otp,
    is_account_locked,
    issue_tokens_for_user,
    record_login_attempt,
    revoke_all_user_sessions,
    revoke_user_session,
    verify_phone_otp,
)


class LoginView(APIView):
    """Authenticate via username/phone and password, returning JWT tokens."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="User Login",
        description="Authenticate using username or BD mobile number with password.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful, tokens returned."),
            401: OpenApiResponse(description="Invalid credentials."),
            429: OpenApiResponse(description="Account locked due to consecutive failed attempts."),
        },
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]
        ip_address = request.META.get("REMOTE_ADDR")

        # Check brute force lockout
        if is_account_locked(identifier):
            return Response(
                {
                    "code": "ACCOUNT_LOCKED",
                    "message": "Account temporarily locked due to multiple failed login attempts. Please try again after 15 minutes.",
                    "details": {},
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Lookup user by phone or username
        user = None
        if validate_bd_phone(identifier):
            normalized_phone = normalize_bd_phone(identifier)
            user = (
                User.objects.filter(phone=normalized_phone).first()
                or User.objects.filter(username=identifier).first()
                or User.objects.filter(username=normalized_phone).first()
                or User.objects.filter(phone=identifier).first()
            )
        else:
            user = User.objects.filter(username=identifier).first()

        if not user or not user.check_password(password):
            record_login_attempt(identifier, ip_address=ip_address, successful=False)
            raise AuthenticationFailed(
                "Invalid credentials. Please verify your username/phone and password."
            )

        if not user.is_active:
            raise AuthenticationFailed("This user account has been deactivated.")

        # Record success
        record_login_attempt(identifier, ip_address=ip_address, successful=True)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Check TOTP if enabled
        if user.is_totp_enabled:
            return Response(
                {
                    "code": "TOTP_REQUIRED",
                    "message": "Two-factor authentication code is required.",
                    "user_id": str(user.id),
                },
                status=status.HTTP_200_OK,
            )

        device_info = {
            "device_id": serializer.validated_data.get("device_id"),
            "device_name": serializer.validated_data.get("device_name"),
            "platform": serializer.validated_data.get("platform"),
            "app_version": serializer.validated_data.get("app_version"),
            "fcm_token": serializer.validated_data.get("fcm_token"),
            "ip_address": ip_address,
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        token_data = issue_tokens_for_user(user, device_info=device_info)
        return Response(token_data, status=status.HTTP_200_OK)


class OTPRequestView(APIView):
    """Request a one-time password delivered via SMS."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Request Phone OTP",
        request=OTPRequestSerializer,
        responses={200: OpenApiResponse(description="OTP sent successfully.")},
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        purpose = serializer.validated_data.get("purpose", "login")

        try:
            generate_phone_otp(phone, purpose=purpose)
        except DjangoValidationError as exc:
            raise ValidationError(detail=str(exc)) from exc

        return Response(
            {"message": "Verification code has been dispatched to your phone."},
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    """Verify phone OTP and obtain JWT tokens."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify Phone OTP",
        request=OTPVerifySerializer,
        responses={200: OpenApiResponse(description="Verification successful.")},
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        purpose = serializer.validated_data.get("purpose", "login")

        try:
            user = verify_phone_otp(phone, code, purpose=purpose)
        except DjangoValidationError as exc:
            raise ValidationError(detail=str(exc)) from exc

        device_info = {
            "device_id": serializer.validated_data.get("device_id"),
            "platform": serializer.validated_data.get("platform"),
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        token_data = issue_tokens_for_user(user, device_info=device_info)
        return Response(token_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """Logout current session and invalidate refresh token."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout",
        request=None,
        responses={200: OpenApiResponse(description="Successfully logged out.")},
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                jti = token.get("jti")
                UserSession.objects.filter(refresh_token_jti=jti, user=request.user).update(
                    revoked_at=timezone.now()
                )
                token.blacklist()
            except Exception:  # noqa: BLE001
                pass

        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


class LogoutAllView(APIView):
    """Revoke all active sessions for current user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout All Sessions",
        request=None,
        responses={200: OpenApiResponse(description="All sessions revoked.")},
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        revoke_all_user_sessions(request.user)
        return Response({"message": "All sessions have been revoked."}, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    """Change authenticated user's password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change Password",
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully.")},
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        assert isinstance(user, User)
        if not user.check_password(serializer.validated_data["old_password"]):
            raise ValidationError({"old_password": "Old password is not correct."})

        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])

        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """Retrieve and update current user's profile and permissions."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get Current Profile", responses={200: UserSerializer}, tags=["Profile"])
    def get(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = UserSerializer(user)
        data = serializer.data
        # Add effective permissions list
        if user.is_superuser:
            data["permissions"] = ["*"]
        else:
            perms = list(
                Role.objects.filter(assigned_users__user=user)
                .values_list("permissions__codename", flat=True)
                .distinct()
            )
            data["permissions"] = [p for p in perms if p]
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update Profile",
        request=UserProfileUpdateSerializer,
        responses={200: UserSerializer},
        tags=["Profile"],
    )
    def patch(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """View and revoke current user sessions."""

    queryset = UserSession.objects.none()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer

    def get_queryset(self) -> Any:
        if getattr(self, "swagger_fake_view", False):
            return UserSession.objects.none()
        assert isinstance(self.request.user, User)
        return UserSession.objects.filter(user=self.request.user)

    @extend_schema(summary="Revoke Session", tags=["Sessions"])
    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request: Request, pk: str | None = None) -> Response:
        assert isinstance(request.user, User)
        session = self.get_object()
        revoke_user_session(session.id, request.user)
        return Response({"message": "Session revoked."}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Users", tags=["User Management"]),
    create=extend_schema(summary="Create User", tags=["User Management"]),
    retrieve=extend_schema(summary="Get User", tags=["User Management"]),
    update=extend_schema(summary="Update User", tags=["User Management"]),
    partial_update=extend_schema(summary="Partial Update User", tags=["User Management"]),
    destroy=extend_schema(summary="Delete User", tags=["User Management"]),
)
class UserManagementViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Admin CRUD for institutional users."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasModulePermission("accounts.manage_users")]
    filterset_fields = ["user_type", "is_active"]
    search_fields = ["username", "full_name", "phone", "email"]

    def get_serializer_class(self) -> Any:
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @extend_schema(
        summary="Assign Role to User",
        request=UserRoleSerializer,
        responses={201: UserRoleSerializer},
        tags=["User Management"],
    )
    @action(detail=True, methods=["post"], url_path="assign-role")
    def assign_role(self, request: Request, pk: str | None = None) -> Response:
        user = self.get_object()
        role_id = request.data.get("role_id")
        branch_id = request.data.get("branch_id")

        role = Role.objects.filter(id=str(role_id), institution_id=user.institution_id).first()
        if not role:
            raise ValidationError({"role_id": "Invalid role for this institution."})

        user_role, _ = UserRole.objects.get_or_create(
            user=user,
            role=role,
            branch_id=branch_id,
        )
        return Response(UserRoleSerializer(user_role).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(summary="List Roles", tags=["Role Management"]),
    create=extend_schema(summary="Create Role", tags=["Role Management"]),
    retrieve=extend_schema(summary="Get Role", tags=["Role Management"]),
    update=extend_schema(summary="Update Role", tags=["Role Management"]),
    partial_update=extend_schema(summary="Partial Update Role", tags=["Role Management"]),
    destroy=extend_schema(summary="Delete Role", tags=["Role Management"]),
)
class RoleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for institutional roles."""

    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    permission_classes = [HasModulePermission("accounts.manage_roles")]
    search_fields = ["name", "code"]
