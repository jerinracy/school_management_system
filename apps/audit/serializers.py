"""Read-only DRF serializers for AuditLog and ActivityLog."""

from rest_framework import serializers

from apps.audit.models import ActivityLog, AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "institution",
            "actor",
            "actor_username",
            "action",
            "module",
            "target_model",
            "target_object_id",
            "target_repr",
            "before_data",
            "after_data",
            "changed_fields",
            "ip_address",
            "user_agent",
            "request_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "institution",
            "actor",
            "actor_username",
            "activity_type",
            "module",
            "description",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
