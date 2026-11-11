"""Authentication, Users, Roles, and Session security models."""

import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel

from .managers import UserManager


class UserType(models.TextChoices):
    SUPERADMIN = "superadmin", "Super Admin"
    ADMIN = "admin", "Institution Admin"
    HEAD_TEACHER = "head_teacher", "Head Teacher"
    ASSISTANT_HEAD = "assistant_head", "Assistant Head Teacher"
    TEACHER = "teacher", "Teacher"
    ACCOUNTANT = "accountant", "Accountant"
    LIBRARIAN = "librarian", "Librarian"
    CLERK = "clerk", "Clerk"
    STAFF = "staff", "Office Staff"
    STUDENT = "student", "Student"
    GUARDIAN = "guardian", "Guardian"
    DRIVER = "driver", "Driver"
    SECURITY = "security", "Security"


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model for multi-tenant School Management System."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        help_text="Tenant institution. Null only for platform superadmins.",
    )
    username = models.CharField(max_length=150, unique=True, db_index=True)
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        help_text="Normalized BD mobile number (+8801XXXXXXXXX).",
    )
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    user_type = models.CharField(
        max_length=30,
        choices=UserType.choices,
        default=UserType.STAFF,
        db_index=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    language_preference = models.CharField(
        max_length=10,
        choices=[("bn", "Bangla"), ("en", "English")],
        default="bn",
    )
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # 2FA / TOTP Support
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    is_totp_enabled = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "phone"],
                condition=models.Q(phone__isnull=False),
                name="unique_phone_per_institution",
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(institution__isnull=True, phone__isnull=False),
                name="unique_superadmin_phone",
            ),
        ]

    def __str__(self) -> str:
        inst_label = self.institution.name_en if self.institution else "Global"
        return f"{self.username} ({self.get_user_type_display()}) - {inst_label}"


class Role(BaseModel):
    """Institutional roles (e.g. Super Admin, Head Teacher, Teacher, Guardian)."""

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    is_system = models.BooleanField(
        default=False,
        help_text="System roles are seeded and protected against deletion.",
    )
    permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="custom_roles",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_role_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code}) - {self.institution.name_en}"


class UserRole(BaseModel):
    """Assignment of role to a user, with optional branch-level scope."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="assigned_users")
    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="branch_user_roles",
    )

    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "branch"],
                name="unique_user_role_branch",
            )
        ]

    def __str__(self) -> str:
        branch_name = f" [{self.branch.code}]" if self.branch else ""
        return f"{self.user.username} -> {self.role.code}{branch_name}"


class OTPPurpose(models.TextChoices):
    LOGIN = "login", "Login"
    PASSWORD_RESET = "password_reset", "Password Reset"
    VERIFY = "verify", "Phone Verification"


class OTPChallenge(BaseModel):
    """Secure phone OTP challenge tracking."""

    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(
        max_length=30,
        choices=OTPPurpose.choices,
        default=OTPPurpose.LOGIN,
    )
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OTP Challenge"
        verbose_name_plural = "OTP Challenges"

    def is_valid(self) -> bool:
        return self.used_at is None and self.attempts < 3 and timezone.now() < self.expires_at


class PlatformType(models.TextChoices):
    WEB = "web", "Web Dashboard"
    ANDROID = "android", "Android App"
    IOS = "ios", "iOS App"


class UserSession(BaseModel):
    """Active user session tracking and token management."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_token_jti = models.CharField(max_length=255, db_index=True)
    device_id = models.CharField(max_length=255, blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    platform = models.CharField(
        max_length=30,
        choices=PlatformType.choices,
        default=PlatformType.WEB,
    )
    app_version = models.CharField(max_length=50, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class LoginAttempt(BaseModel):
    """Log for login attempts to enforce rate limiting and lockout."""

    identifier = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    successful = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Login Attempt"
        verbose_name_plural = "Login Attempts"


class PasswordResetToken(BaseModel):
    """Secure password reset token."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_resets")
    token_hash = models.CharField(max_length=128, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"

    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at
