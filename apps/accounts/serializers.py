"""DRF Serializers for Authentication, Users, Roles, and Sessions."""

from typing import Any

from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.core.utils.phone import normalize_bd_phone
from apps.institutions.models import Branch

from .models import PlatformType, Role, User, UserRole, UserSession


class LoginSerializer(serializers.Serializer):
    """Serializer for username/phone and password login."""

    identifier = serializers.CharField(
        required=True,
        help_text="Username or Bangladeshi mobile number (+8801XXXXXXXXX / 01XXXXXXXXX).",
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )
    device_id = serializers.CharField(required=False, allow_blank=True, default="")
    device_name = serializers.CharField(required=False, allow_blank=True, default="")
    platform = serializers.ChoiceField(
        choices=PlatformType.choices,
        required=False,
        default=PlatformType.WEB,
    )
    app_version = serializers.CharField(required=False, allow_blank=True, default="")
    fcm_token = serializers.CharField(required=False, allow_blank=True, default="")


class OTPRequestSerializer(serializers.Serializer):
    """Serializer for requesting phone OTP."""

    phone = serializers.CharField(required=True)
    purpose = serializers.ChoiceField(
        choices=["login", "password_reset", "verify"],
        required=False,
        default="login",
    )

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)


class OTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying phone OTP."""

    phone = serializers.CharField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    purpose = serializers.ChoiceField(
        choices=["login", "password_reset", "verify"],
        required=False,
        default="login",
    )
    device_id = serializers.CharField(required=False, allow_blank=True, default="")
    platform = serializers.ChoiceField(
        choices=PlatformType.choices, required=False, default=PlatformType.WEB
    )

    def validate_phone(self, value: str) -> str:
        return normalize_bd_phone(value)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset token/link."""

    identifier = serializers.CharField(required=True, help_text="Username, phone, or email.")


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for resetting password via token."""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for auth.Permission."""

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type"]


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role."""

    permission_codenames: Any = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="codename",
        source="permissions",
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "institution",
            "name",
            "code",
            "is_system",
            "permissions",
            "permission_codenames",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "is_system", "created_at", "updated_at"]


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole assignments."""

    role_name = serializers.CharField(source="role.name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    branch_code = serializers.CharField(source="branch.code", read_only=True)

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user",
            "role",
            "role_name",
            "role_code",
            "branch",
            "branch_code",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User details."""

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "institution",
            "username",
            "phone",
            "email",
            "full_name",
            "user_type",
            "is_active",
            "must_change_password",
            "language_preference",
            "avatar",
            "is_totp_enabled",
            "roles",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "institution", "is_totp_enabled", "date_joined", "last_login"]

    def get_roles(self, obj: User) -> list[str]:
        return list(obj.user_roles.values_list("role__code", flat=True))


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new user by Admin."""

    password = serializers.CharField(write_only=True, required=False)
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "institution",
            "branch",
            "username",
            "phone",
            "email",
            "full_name",
            "user_type",
            "is_active",
            "must_change_password",
            "language_preference",
            "password",
        ]
        read_only_fields = ["id", "institution"]

    def validate_phone(self, value: str | None) -> str | None:
        if value:
            return normalize_bd_phone(value)
        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        branch = validated_data.pop("branch", None)
        if branch and getattr(branch, "institution", None):
            validated_data["institution"] = branch.institution

        password = validated_data.pop("password", None)
        user = User.objects.create_user(password=password, **validated_data)

        if branch:
            role_code = user.user_type if user.user_type else "staff"
            role, _ = Role.objects.get_or_create(
                institution=user.institution,
                code=role_code,
                defaults={"name": role_code.capitalize()},
            )
            UserRole.objects.get_or_create(user=user, role=role, defaults={"branch": branch})

        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for self-updating user profile."""

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "language_preference",
            "avatar",
        ]


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for active user sessions."""

    class Meta:
        model = UserSession
        fields = [
            "id",
            "device_id",
            "device_name",
            "platform",
            "app_version",
            "ip_address",
            "last_seen_at",
            "is_active",
        ]
        read_only_fields = fields


class TOTPSetupSerializer(serializers.Serializer):
    """Serializer for setting up TOTP."""

    secret = serializers.CharField(read_only=True)
    otpauth_url = serializers.CharField(read_only=True)


class TOTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying and activating TOTP."""

    code = serializers.CharField(required=True, min_length=6, max_length=6)
