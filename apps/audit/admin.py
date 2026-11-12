from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.audit.models import ActivityLog, AuditLog


class ReadOnlyAuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAuditAdmin):
    list_display = (
        "created_at",
        "institution",
        "actor_username",
        "action",
        "module",
        "target_model",
    )
    list_filter = ("action", "module", "target_model")
    search_fields = ("actor_username", "target_object_id", "target_repr")


@admin.register(ActivityLog)
class ActivityLogAdmin(ReadOnlyAuditAdmin):
    list_display = ("created_at", "institution", "actor_username", "activity_type", "module")
    list_filter = ("activity_type", "module")
    search_fields = ("actor_username", "description")
