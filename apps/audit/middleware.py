"""Middleware to capture request context (actor, IP, User-Agent, request ID) in contextvars."""

import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse


@dataclass(frozen=True)
class AuditRequestContext:
    request: HttpRequest | None = None
    ip_address: str | None = None
    user_agent: str = ""
    request_id: str = ""


_audit_context: ContextVar[AuditRequestContext | None] = ContextVar(
    "audit_request_context",
    default=None,
)


def get_current_audit_context() -> AuditRequestContext | None:
    return _audit_context.get()


def extract_client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    remote_addr = request.META.get("REMOTE_ADDR", "")
    return str(remote_addr) if remote_addr else None


class AuditContextMiddleware:
    """Stores HTTP request metadata in a contextvar for automatic audit attribution."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        req_id = str(request.META.get("HTTP_X_REQUEST_ID") or uuid.uuid4())
        user_agent = str(request.META.get("HTTP_USER_AGENT", ""))[:512]
        ctx = AuditRequestContext(
            request=request,
            ip_address=extract_client_ip(request),
            user_agent=user_agent,
            request_id=req_id,
        )
        token = _audit_context.set(ctx)
        try:
            return self.get_response(request)
        finally:
            _audit_context.reset(token)
