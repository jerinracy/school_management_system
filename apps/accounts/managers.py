"""Custom manager for the User model."""

from typing import Any

from django.contrib.auth.models import BaseUserManager

from apps.core.utils.phone import normalize_bd_phone


class UserManager(BaseUserManager):
    """Custom manager for accounts.User."""

    def create_user(
        self,
        username: str,
        password: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        **extra_fields: Any,
    ) -> Any:
        """Create and save a standard user."""
        if not username:
            raise ValueError("The Username field must be set.")

        normalized_phone = None
        if phone:
            normalized_phone = normalize_bd_phone(phone)

        normalized_email = None
        if email:
            normalized_email = self.normalize_email(email)

        user: Any = self.model(
            username=username,
            phone=normalized_phone,
            email=normalized_email,
            **extra_fields,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        username: str,
        password: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        **extra_fields: Any,
    ) -> Any:
        """Create and save a global platform superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "superadmin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            username=username,
            password=password,
            phone=phone,
            email=email,
            **extra_fields,
        )
