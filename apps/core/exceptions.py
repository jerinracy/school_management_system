"""Standardized exception handling and error envelope."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base application exception for business logic errors."""

    def __init__(self, message: str, code: str = "APPLICATION_ERROR", details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Transform DRF and Python exceptions into the standard error envelope.

    Standard envelope:
    {
        "code": "ERROR_CODE",
        "message": "Human readable error summary",
        "details": { ... }
    }
    """
    # Call DRF's default exception handler first to get the standard response object
    response = exception_handler(exc, context)

    if response is not None:
        code = "API_ERROR"
        message = "An error occurred while processing the request."
        details: Any = response.data

        if isinstance(exc, ValidationError):
            code = "VALIDATION_ERROR"
            message = "Validation failed for the submitted data."
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            code = "AUTHENTICATION_REQUIRED"
            message = "Authentication credentials were not provided or are invalid."
        elif isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
            code = "PERMISSION_DENIED"
            message = "You do not have permission to perform this action."
        elif isinstance(exc, (NotFound, Http404)):
            code = "NOT_FOUND"
            message = "The requested resource was not found."
        elif isinstance(exc, APIException):
            code = getattr(exc, "default_code", "API_ERROR").upper()
            if isinstance(response.data, dict) and "detail" in response.data:
                message = str(response.data["detail"])
                details = {}

        response.data = {
            "code": code,
            "message": message,
            "details": details,
        }
        return response

    # Handle domain ApplicationError if raised directly
    if isinstance(exc, ApplicationError):
        return Response(
            {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Unhandled server errors (500)
    logger.exception("Unhandled server exception in request: %s", str(exc), exc_info=exc)
    return Response(
        {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please contact support.",
            "details": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
