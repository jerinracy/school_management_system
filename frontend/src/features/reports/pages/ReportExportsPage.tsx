import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Download,
  Plus,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Calendar,
  X,
  FileText,
} from "lucide-react";
import {
  reportsApi,
  DATASET_SPEC,
  type ReportDatasetType,
  type ExportFormatType,
  type ExportJobStatusType,
} from "../api/reportsApi";
import {
  quickExportSchema,
  type QuickExportFormData,
} from "../schemas/reportsSchemas";

export const ReportExportsPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [formatFilter, setFormatFilter] = useState<string>("all");
  const [isQuickExportOpen, setIsQuickExportOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch exports
  const { data: exportsData, isLoading } = useQuery({
    queryKey: ["report-exports", { statusFilter, formatFilter }],
    queryFn: () =>
      reportsApi.getReportExports({
        status: statusFilter !== "all" ? statusFilter : undefined,
        export_format: formatFilter !== "all" ? formatFilter : undefined,
      }),
  });

  const exportsList = exportsData?.results || [];

  // Quick export form
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { isSubmitting },
  } = useForm<QuickExportFormData>({
    resolver: zodResolver(quickExportSchema) as never,
    defaultValues: {
      dataset: "students",
      export_format: "csv",
    },
  });

  const selectedDataset = watch("dataset");
  const [selectedColumns, setSelectedColumns] = useState<string[]>([
    "student_id",
    "name_en",
    "gender",
    "status",
  ]);

  const handleDatasetChange = (ds: ReportDatasetType) => {
    setValue("dataset", ds);
    const initialCols = DATASET_SPEC[ds].columns.slice(0, 4).map((c) => c.key);
    setSelectedColumns(initialCols);
  };

  const handleColumnToggle = (colKey: string) => {
    if (selectedColumns.includes(colKey)) {
      if (selectedColumns.length > 1) {
        setSelectedColumns(selectedColumns.filter((c) => c !== colKey));
      }
    } else {
      setSelectedColumns([...selectedColumns, colKey]);
    }
  };

  // Run quick export mutation
  const runExportMutation = useMutation({
    mutationFn: (data: QuickExportFormData) =>
      reportsApi.runReportExport({
        dataset: data.dataset,
        export_format: data.export_format,
        selected_columns: selectedColumns,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["report-exports"] });
      setIsQuickExportOpen(false);
      reset();
      setFeedback({
        type: "success",
        message: t("reports.exportTriggeredSuccess", "Export job initiated successfully"),
      });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const onSubmit = (data: QuickExportFormData) => {
    runExportMutation.mutate(data);
  };

  // Download export file
  const handleDownload = async (id: string, dataset: string, format: string) => {
    try {
      const blob = await reportsApi.downloadReportExport(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dataset}-${id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Download failed";
      setFeedback({ type: "error", message });
    }
  };

  const getStatusBadge = (status: ExportJobStatusType) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle className="w-3 h-3 mr-1" />
            Completed
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
            <Clock className="w-3 h-3 mr-1 animate-spin" />
            Processing
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            <XCircle className="w-3 h-3 mr-1" />
            Failed
          </span>
        );
      case "pending":
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
            <Clock className="w-3 h-3 mr-1" />
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <Download className="w-7 h-7 text-emerald-600" />
            {t("reports.reportExportsTitle", "Data Export Center")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "reports.reportExportsSubtitle",
              "Execute on-demand data extracts, download compiled files (CSV, Excel, PDF), and manage export retention"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsQuickExportOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("reports.runQuickExportBtn", "Run On-Demand Export")}
        </button>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-lg flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          <span className="text-sm font-medium">{feedback.message}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-xs underline hover:no-underline ml-4"
          >
            {t("common.dismiss", "Dismiss")}
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-500 mr-1">Status:</span>
          {["all", "completed", "processing", "pending", "failed"].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition ${
                statusFilter === st
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-500 mr-1">Format:</span>
          {["all", "csv", "xlsx", "pdf"].map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => setFormatFilter(fmt)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium uppercase font-mono transition ${
                formatFilter === fmt
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Exports Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading export jobs...")}</p>
          </div>
        ) : exportsList.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("reports.noExportsFound", "No Export Jobs on Record")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("reports.noExportsDesc", "Generate custom CSV, Excel, or PDF report extracts to download.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("reports.dataset", "Target Dataset")}</th>
                  <th className="px-4 py-3 text-center">{t("reports.format", "Format")}</th>
                  <th className="px-4 py-3">{t("reports.status", "Status")}</th>
                  <th className="px-3 py-3 text-center">{t("reports.rowCount", "Rows")}</th>
                  <th className="px-4 py-3">{t("reports.generatedAt", "Generated At")}</th>
                  <th className="px-4 py-3">{t("reports.expiresAt", "Expires At")}</th>
                  <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {exportsList.map((job) => {
                  const spec = DATASET_SPEC[job.dataset];

                  return (
                    <tr key={job.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3 font-semibold text-gray-900 text-xs">
                        <div>{spec?.label || job.dataset}</div>
                        <div className="text-[11px] text-gray-400 font-mono font-normal">
                          Columns: {job.selected_columns?.length || 0}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-mono text-xs font-bold uppercase px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                          {job.export_format}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {getStatusBadge(job.status)}
                      </td>
                      <td className="px-3 py-3 text-center font-mono text-xs font-bold text-gray-900">
                        {job.row_count}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-gray-400" />
                          {new Date(job.created_at).toLocaleString("en-BD", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500 font-mono text-[11px]">
                        {job.expires_at
                          ? new Date(job.expires_at).toLocaleDateString("en-BD", {
                              day: "numeric",
                              month: "short",
                            })
                          : "7 days"}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap text-right">
                        {job.status === "completed" ? (
                          <button
                            type="button"
                            onClick={() => void handleDownload(job.id, job.dataset, job.export_format)}
                            className="inline-flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition"
                          >
                            <Download className="w-3.5 h-3.5 mr-1" />
                            {t("reports.downloadFile", "Download File")}
                          </button>
                        ) : job.status === "failed" ? (
                          <span className="text-xs text-red-600 flex items-center justify-end gap-1">
                            <AlertCircle className="w-3.5 h-3.5" />
                            {job.error_message || "Export error"}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400 italic">Processing...</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Quick On-Demand Export */}
      {isQuickExportOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Download className="w-5 h-5 text-emerald-600" />
                {t("reports.quickExportModalTitle", "Run On-Demand Export")}
              </h3>
              <button
                type="button"
                onClick={() => setIsQuickExportOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                void handleSubmit(onSubmit)(e);
              }}
              className="mt-4 space-y-4"
            >
              {/* Dataset Selection */}
              <div>
                <label htmlFor="quick_dataset" className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Dataset *
                </label>
                <select
                  id="quick_dataset"
                  value={selectedDataset}
                  onChange={(e) => handleDatasetChange(e.target.value as ReportDatasetType)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-emerald-500 focus:border-emerald-500"
                >
                  {Object.entries(DATASET_SPEC).map(([key, spec]) => (
                    <option key={key} value={key}>
                      {spec.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Column Selection Checklist */}
              <div>
                <span className="block text-xs font-semibold text-gray-700 mb-1">
                  Include Columns ({selectedColumns.length}) *
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-3 bg-gray-50 rounded-xl border border-gray-200 max-h-40 overflow-y-auto">
                  {DATASET_SPEC[selectedDataset]?.columns.map((col) => {
                    const isChecked = selectedColumns.includes(col.key);
                    return (
                      <button
                        type="button"
                        key={col.key}
                        onClick={() => handleColumnToggle(col.key)}
                        className={`flex items-center gap-2 p-2 rounded-lg border text-left text-xs transition cursor-pointer ${
                          isChecked
                            ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-semibold"
                            : "bg-white border-gray-200 text-gray-600 hover:bg-gray-100"
                        }`}
                      >
                        <CheckCircle
                          className={`w-4 h-4 shrink-0 ${isChecked ? "text-emerald-600" : "text-gray-300"}`}
                        />
                        <span className="truncate">{col.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Format Radio Selection */}
              <div>
                <span className="block text-xs font-semibold text-gray-700 mb-1">
                  Export File Format *
                </span>
                <div className="grid grid-cols-3 gap-3">
                  {(["csv", "xlsx", "pdf"] as ExportFormatType[]).map((fmt) => (
                    <label
                      key={fmt}
                      className="flex items-center gap-2 p-2.5 rounded-lg border border-gray-200 bg-white cursor-pointer hover:bg-gray-50 text-xs font-medium uppercase font-mono"
                    >
                      <input
                        type="radio"
                        value={fmt}
                        {...register("export_format")}
                        className="text-emerald-600 focus:ring-emerald-500"
                      />
                      <span>{fmt}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsQuickExportOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || runExportMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || runExportMutation.isPending
                    ? t("common.saving", "Processing...")
                    : t("reports.startExport", "Start Export")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
