"""AppConfig for Payroll Management module."""

from django.apps import AppConfig


class PayrollConfig(AppConfig):
    """Django AppConfig for apps.payroll."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payroll"
    verbose_name = "Payroll Management"
