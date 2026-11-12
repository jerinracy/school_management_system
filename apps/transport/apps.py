from django.apps import AppConfig


class TransportConfig(AppConfig):
    """AppConfig for Transport Management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transport"
    verbose_name = "Transport Management"
