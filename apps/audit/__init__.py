default_app_config = "apps.audit.apps.AuditConfig"


def record(*args: object, **kwargs: object) -> object:
    """Lazy proxy to audit_service.record to avoid circular imports at startup."""
    from apps.audit.services.audit_service import record as _record

    return _record(*args, **kwargs)  # type: ignore[arg-type]
