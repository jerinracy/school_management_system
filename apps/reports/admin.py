from django.contrib import admin

from apps.reports.models import BulkImportJob, ReportDefinition, ReportExportJob

admin.site.register(ReportDefinition)
admin.site.register(ReportExportJob)
admin.site.register(BulkImportJob)
