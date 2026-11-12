from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit Logging & Activity Tracking"

    def ready(self) -> None:
        from apps.audit import signals  # noqa: F401
