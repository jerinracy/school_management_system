"""Audit logging & activity tracking service with PII/secret redaction."""

import re
from typing import Any

from django.http import HttpRequest

from apps.accounts.models import User
from apps.audit.middleware import extract_client_ip, get_current_audit_context
from apps.audit.models import ActivityLog, AuditLog
from apps.institutions.models import Institution

SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "token",
    "secret",
    "otp",
    "pin",
    "nid",
    "biometric",
    "raw_image",
    "api_key",
    "private_key",
    "hash",
)

PHONE_KEY_SUBSTRINGS = ("phone", "mobile", "contact_number")
BD_PHONE_REGEX = re.compile(r"(\+?8801\d)(\d{4})(\d{4})")


def mask_phone_number(value: str) -> str:
    """Mask middle digits of phone numbers so guardian/student phones are never exposed raw."""
    stripped = value.strip()
    match = BD_PHONE_REGEX.fullmatch(stripped)
    if match:
        return f"{match.group(1)}****{match.group(3)}"
    if len(stripped) >= 7:
        return f"{stripped[:4]}****{stripped[-3:]}"
    return "****"


def sanitize_payload(data: Any) -> Any:
    """Recursively redact secrets/NIDs/biometrics and mask phone numbers in JSON payloads."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(sub in key_lower for sub in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[str(k)] = "[REDACTED]"
            elif any(sub in key_lower for sub in PHONE_KEY_SUBSTRINGS) and isinstance(v, str):
                sanitized[str(k)] = mask_phone_number(v)
            else:
                sanitized[str(k)] = sanitize_payload(v)
        return sanitized
    if isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    if isinstance(data, (str, int, float, bool)) or data is None:
        return data
    return str(data)


def compute_changed_fields(
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
) -> list[str]:
    """Return sorted list of keys whose values differ between before_data and after_data."""
    if not before_data and not after_data:
        return []
    before = before_data or {}
    after = after_data or {}
    all_keys = set(before.keys()) | set(after.keys())
    return sorted(k for k in all_keys if before.get(k) != after.get(k))


def _resolve_actor_and_inst(
    effective_request: HttpRequest | None,
    actor: User | None,
    institution: Institution | None,
) -> tuple[User | None, Institution | None]:
    resolved_actor = actor
    if resolved_actor is None and effective_request is not None:
        req_user = getattr(effective_request, "user", None)
        if isinstance(req_user, User) and req_user.is_authenticated:
            resolved_actor = req_user

    resolved_inst = institution
    if resolved_inst is None and effective_request is not None:
        resolved_inst = getattr(effective_request, "institution", None)
    if resolved_inst is None and resolved_actor is not None:
        resolved_inst = getattr(resolved_actor, "institution", None)
    return resolved_actor, resolved_inst


def _resolve_request_metadata(
    *,
    request: HttpRequest | None,
    actor: User | None,
    institution: Institution | None,
    ip_address: str | None,
    user_agent: str,
    request_id: str,
) -> tuple[User | None, Institution | None, str | None, str, str]:
    ctx = get_current_audit_context()
    effective_request = request or (ctx.request if ctx else None)
    resolved_actor, resolved_inst = _resolve_actor_and_inst(effective_request, actor, institution)

    resolved_ip = ip_address or (
        extract_client_ip(effective_request)
        if effective_request is not None
        else (ctx.ip_address if ctx else None)
    )
    resolved_ua = user_agent or (
        str(effective_request.META.get("HTTP_USER_AGENT", ""))[:512]
        if effective_request is not None
        else (ctx.user_agent if ctx else "")
    )
    resolved_req_id = request_id or (ctx.request_id if ctx else "")
    return resolved_actor, resolved_inst, resolved_ip, resolved_ua, resolved_req_id


def record(
    *,
    action: str,
    module: str,
    target_model: str,
    target_object_id: Any = "",
    target_repr: str = "",
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    actor: User | None = None,
    institution: Institution | None = None,
    request: HttpRequest | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    request_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Create an immutable AuditLog entry with automatic diffing and PII/secret redaction."""
    resolved_actor, resolved_inst, resolved_ip, resolved_ua, resolved_req_id = (
        _resolve_request_metadata(
            request=request,
            actor=actor,
            institution=institution,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
    )

    clean_before = sanitize_payload(before_data or {})
    clean_after = sanitize_payload(after_data or {})
    clean_meta = sanitize_payload(metadata or {})
    changed = compute_changed_fields(clean_before, clean_after)

    return AuditLog.objects.create(
        institution=resolved_inst,
        actor=resolved_actor,
        actor_username=resolved_actor.username if resolved_actor else "",
        action=action,
        module=module,
        target_model=target_model,
        target_object_id=str(target_object_id) if target_object_id is not None else "",
        target_repr=str(target_repr)[:255],
        before_data=clean_before,
        after_data=clean_after,
        changed_fields=changed,
        ip_address=resolved_ip,
        user_agent=resolved_ua[:512],
        request_id=resolved_req_id[:64],
        metadata=clean_meta,
    )


def record_activity(
    *,
    activity_type: str,
    module: str,
    description: str,
    actor: User | None = None,
    institution: Institution | None = None,
    request: HttpRequest | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    """Create an immutable ActivityLog entry."""
    resolved_actor, resolved_inst, resolved_ip, resolved_ua, _ = _resolve_request_metadata(
        request=request,
        actor=actor,
        institution=institution,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id="",
    )
    clean_meta = sanitize_payload(metadata or {})
    return ActivityLog.objects.create(
        institution=resolved_inst,
        actor=resolved_actor,
        actor_username=resolved_actor.username if resolved_actor else "",
        activity_type=activity_type,
        module=module,
        description=description[:500],
        ip_address=resolved_ip,
        user_agent=resolved_ua[:512],
        metadata=clean_meta,
    )
