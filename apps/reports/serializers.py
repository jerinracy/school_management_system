"""DRF serializers for Dashboard KPIs, Report Definitions, Exports & Bulk Imports."""

from rest_framework import serializers

from apps.reports.models import (
    BulkImportJob,
    BulkImportTarget,
    ExportFormat,
    ReportDataset,
    ReportDefinition,
    ReportExportJob,
)


class ReportDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportDefinition
        fields = [
            "id",
            "institution",
            "name",
            "dataset",
            "selected_columns",
            "filters",
            "default_format",
            "created_by",
            "is_shared",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_by", "created_at", "updated_at"]


class ReportExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportExportJob
        fields = [
            "id",
            "institution",
            "definition",
            "dataset",
            "selected_columns",
            "filters",
            "export_format",
            "status",
            "file",
            "row_count",
            "expires_at",
            "requested_by",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class RunReportExportSerializer(serializers.Serializer):
    dataset = serializers.ChoiceField(choices=ReportDataset.choices)
    selected_columns = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    filters = serializers.DictField(required=False, default=dict)
    export_format = serializers.ChoiceField(
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
    )


class BulkImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkImportJob
        fields = [
            "id",
            "institution",
            "target_type",
            "status",
            "file",
            "dry_run",
            "total_rows",
            "valid_rows",
            "error_rows",
            "errors_summary",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = fields


class BulkImportUploadSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=BulkImportTarget.choices)
    file = serializers.FileField()
    dry_run = serializers.BooleanField(default=True)
