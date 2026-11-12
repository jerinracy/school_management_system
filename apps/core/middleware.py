"""Security headers, admin 2FA enforcement, and optional IP allowlist middleware."""

import ipaddress
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.accounts.models import User, UserType
from apps.audit.middleware import extract_client_ip

ADMIN_2FA_EXEMPT_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/health/",
    "/api/schema/",
    "/admin/",
)


class SecurityHeadersMiddleware:
    """Attach hardened HTTP security headers to all responses."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        csp = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if csp:
            response.setdefault("Content-Security-Policy", csp)
        return response


def _is_ip_allowed(client_ip: str | None, allowed_entries: list[str]) -> bool:
    if not allowed_entries:
        return True
    if not client_ip:
        return False
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for entry in allowed_entries:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def check_admin_security(request: HttpRequest, user: object) -> tuple[str, str] | None:
    """Return (error_code, message) if an admin user fails IP allowlist or 2FA policy."""
    if not isinstance(user, User) or not user.is_authenticated:
        return None

    if user.user_type not in {UserType.SUPERADMIN, UserType.ADMIN}:
        return None

    path = request.path or ""
    if any(path.startswith(prefix) for prefix in ADMIN_2FA_EXEMPT_PREFIXES):
        return None

    global_ips = list(getattr(settings, "ADMIN_ALLOWED_IPS", []) or [])
    inst = getattr(user, "institution", None)
    inst_ips = (
        list((inst.settings or {}).get("admin_allowed_ips", []))
        if inst and isinstance(inst.settings, dict)
        else []
    )
    allowed_ips = inst_ips or global_ips
    if allowed_ips and not _is_ip_allowed(extract_client_ip(request), allowed_ips):
        return ("ip_restricted", "Admin access is restricted from this IP address.")

    if getattr(settings, "ENFORCE_ADMIN_2FA", False) and not user.is_totp_enabled:
        return (
            "2fa_required",
            "Two-factor authentication (2FA) must be enabled for admin accounts.",
        )

    return None


class AdminSecurityMiddleware:
    """Enforce TOTP 2FA and optional IP allowlists for session-authenticated admin requests."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        violation = check_admin_security(request, getattr(request, "user", None))
        if violation is not None:
            code, message = violation
            return JsonResponse({"code": code, "message": message}, status=403)
        return self.get_response(request)
