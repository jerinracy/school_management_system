from django.apps import AppConfig


class LibraryConfig(AppConfig):
    """AppConfig for Library Management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.library"
    verbose_name = "Library Management"
