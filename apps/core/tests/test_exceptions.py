"""Unit tests for exception handling and error envelope."""

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.core.exceptions import ApplicationError, custom_exception_handler


class TestExceptionHandler:
    def test_validation_error_envelope(self) -> None:
        exc = ValidationError({"phone": ["Invalid phone number."]})
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "VALIDATION_ERROR"
        assert "Validation failed" in response.data["message"]
        assert "phone" in response.data["details"]

    def test_authentication_error_envelope(self) -> None:
        exc = AuthenticationFailed("Token is invalid.")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "AUTHENTICATION_REQUIRED"

    def test_permission_denied_envelope(self) -> None:
        exc = PermissionDenied("Access restricted.")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "PERMISSION_DENIED"

    def test_not_found_envelope(self) -> None:
        exc = NotFound("Resource not found.")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "NOT_FOUND"

    def test_application_error_envelope(self) -> None:
        exc = ApplicationError(message="Insufficient balance", code="INSUFFICIENT_FEE_BALANCE")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "INSUFFICIENT_FEE_BALANCE"
        assert response.data["message"] == "Insufficient balance"

    def test_unhandled_exception_envelope(self) -> None:
        exc = RuntimeError("Database deadlocked unexpectedly")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["code"] == "INTERNAL_SERVER_ERROR"
