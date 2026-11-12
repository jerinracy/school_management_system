"""DRF Views & ViewSets for Dashboard KPIs, Report Builder, Exports & Bulk Imports."""

from datetime import date
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.mixins import TenantScopedMixin
from apps.reports.models import BulkImportJob, ExportFormat, ReportDefinition, ReportExportJob
from apps.reports.permissions import CanAccessReports, CanManageReports, CanViewReports
from apps.reports.serializers import (
    BulkImportJobSerializer,
    BulkImportUploadSerializer,
    ReportDefinitionSerializer,
    ReportExportJobSerializer,
    RunReportExportSerializer,
)
from apps.reports.services import (
    get_dashboard_kpis,
    get_import_template_csv,
    run_bulk_import,
    validate_report_spec,
)
from apps.reports.services.report_service import create_and_run_export


class DashboardKPIView(APIView):
    """Role-scoped, cached dashboard KPI summary."""

    permission_classes = [IsAuthenticated, CanViewReports]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
            )
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        user = request.user
        if not isinstance(user, User):
            return Response({"detail": "Authentication required."}, status=401)
        institution = getattr(request, "institution", None) or user.institution
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)

        raw_date = request.query_params.get("date")
        try:
            target_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError as exc:
            raise DRFValidationError({"date": "Invalid date format. Use YYYY-MM-DD."}) from exc

        data = get_dashboard_kpis(
            institution=institution,
            user=user,
            target_date=target_date,
        )
        return Response(data, status=status.HTTP_200_OK)


class ReportDefinitionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for saved whitelisted report definitions."""

    queryset = ReportDefinition.objects.select_related("created_by")
    serializer_class = ReportDefinitionSerializer
    permission_classes = [IsAuthenticated, CanAccessReports]
    filterset_fields = ["dataset", "is_shared"]
    search_fields = ["name"]

    def get_queryset(self) -> QuerySet[ReportDefinition]:
        return super().get_queryset().filter(is_deleted=False)

    def perform_create(self, serializer: Any) -> None:
        try:
            _, cols, clean_filters = validate_report_spec(
                dataset=serializer.validated_data["dataset"],
                selected_columns=serializer.validated_data.get("selected_columns"),
                filters=serializer.validated_data.get("filters"),
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc

        super().perform_create(serializer)
        user = self.request.user
        serializer.instance.selected_columns = cols
        serializer.instance.filters = clean_filters
        if isinstance(user, User):
            serializer.instance.created_by = user
        serializer.instance.save(update_fields=["selected_columns", "filters", "created_by"])

    @extend_schema(responses={201: ReportExportJobSerializer})
    @action(detail=True, methods=["post"], url_path="export")
    def export(self, request: Request, pk: Any = None) -> Response:
        definition = self.get_object()
        user = request.user if isinstance(request.user, User) else None
        fmt = request.data.get("export_format") or definition.default_format
        if fmt not in {c.value for c in ExportFormat}:
            raise DRFValidationError({"export_format": "Unsupported export format."})

        try:
            job = create_and_run_export(
                institution=definition.institution,
                dataset=definition.dataset,
                selected_columns=list(definition.selected_columns),
                filters=dict(definition.filters or {}),
                export_format=fmt,
                requested_by=user,
                definition_id=definition.id,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc

        return Response(ReportExportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ReportExportJobViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """List, run, and download whitelisted report exports."""

    queryset = ReportExportJob.objects.select_related("definition", "requested_by")
    serializer_class = ReportExportJobSerializer
    permission_classes = [IsAuthenticated, CanAccessReports]
    filterset_fields = ["dataset", "export_format", "status"]

    @extend_schema(request=RunReportExportSerializer, responses={201: ReportExportJobSerializer})
    @action(
        detail=False,
        methods=["post"],
        url_path="run",
        permission_classes=[IsAuthenticated, CanManageReports],
    )
    def run(self, request: Request) -> Response:
        serializer = RunReportExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):
            return Response({"detail": "Authentication required."}, status=401)
        institution = getattr(request, "institution", None) or user.institution
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)

        try:
            job = create_and_run_export(
                institution=institution,
                dataset=serializer.validated_data["dataset"],
                selected_columns=serializer.validated_data.get("selected_columns"),
                filters=serializer.validated_data.get("filters"),
                export_format=serializer.validated_data["export_format"],
                requested_by=user,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc

        return Response(ReportExportJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request: Request, pk: Any = None) -> HttpResponse:
        job = self.get_object()
        if not job.file:
            return Response({"detail": "Export file is not available."}, status=404)

        content_types = {
            ExportFormat.CSV: "text/csv",
            ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ExportFormat.PDF: "application/pdf",
        }
        ext = job.export_format
        with job.file.open("rb") as fh:
            data = fh.read()
        resp = HttpResponse(data, content_type=content_types.get(ext, "application/octet-stream"))
        resp["Content-Disposition"] = f'attachment; filename="{job.dataset}-{job.id}.{ext}"'
        return resp


class BulkImportJobViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Bulk import template download, dry-run validation & commit endpoints."""

    queryset = BulkImportJob.objects.select_related("uploaded_by")
    serializer_class = BulkImportJobSerializer
    permission_classes = [IsAuthenticated, CanAccessReports]
    filterset_fields = ["target_type", "status", "dry_run"]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="target_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request: Request) -> HttpResponse:
        target_type = request.query_params.get("target_type", "")
        try:
            csv_bytes = get_import_template_csv(target_type)
        except DjangoValidationError as exc:
            raise DRFValidationError({"target_type": exc.messages}) from exc

        resp = HttpResponse(csv_bytes, content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{target_type}_template.csv"'
        return resp

    @extend_schema(request=BulkImportUploadSerializer, responses={201: BulkImportJobSerializer})
    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAuthenticated, CanManageReports],
    )
    def upload(self, request: Request) -> Response:
        serializer = BulkImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):
            return Response({"detail": "Authentication required."}, status=401)
        institution = getattr(request, "institution", None) or user.institution
        if institution is None:
            return Response({"detail": "Institution context required."}, status=400)

        try:
            job = run_bulk_import(
                institution=institution,
                target_type=serializer.validated_data["target_type"],
                file_obj=serializer.validated_data["file"],
                uploaded_by=user,
                dry_run=serializer.validated_data["dry_run"],
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.messages}) from exc

        return Response(BulkImportJobSerializer(job).data, status=status.HTTP_201_CREATED)
