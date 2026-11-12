"""App configuration for Homework, Assignments & Learning Management."""

from django.apps import AppConfig


class HomeworkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.homework"
    verbose_name = "Homework & Learning Management"
