import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Upload,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileSpreadsheet,
  Calendar,
  Eye,
  Info,
} from "lucide-react";
import {
  reportsApi,
  type BulkImportTargetType,
  type BulkImportJob,
  type BulkImportStatusType,
} from "../api/reportsApi";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const BulkImportsPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTarget, setActiveTarget] = useState<BulkImportTargetType>("students");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDryRun, setIsDryRun] = useState<boolean>(true);
  const [selectedJob, setSelectedJob] = useState<BulkImportJob | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch bulk import jobs
  const { data: jobsData, isLoading } = useQuery({
    queryKey: ["bulk-imports", activeTarget],
    queryFn: () => reportsApi.getBulkImports({ target_type: activeTarget }),
  });

  const jobs = jobsData?.results || [];

  // Download template CSV
  const handleDownloadTemplate = async () => {
    try {
      const blob = await reportsApi.downloadBulkImportTemplate(activeTarget);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeTarget}_template.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to download template";
      setFeedback({ type: "error", message: msg });
    }
  };

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error("Please select a CSV file to upload");
      return reportsApi.uploadBulkImport(activeTarget, selectedFile, isDryRun);
    },
    onSuccess: (job: BulkImportJob) => {
      void queryClient.invalidateQueries({ queryKey: ["bulk-imports"] });
      setSelectedFile(null);
      setSelectedJob(job);
      const msg = isDryRun
        ? t("reports.validationCompleted", "Dry-run validation completed. Inspect results below.")
        : t("reports.importCommitted", "Data successfully imported and committed to database.");
      setFeedback({ type: "success", message: msg });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.endsWith(".csv")) {
        setFeedback({ type: "error", message: "Only standard CSV files (.csv) are supported." });
        return;
      }
      setSelectedFile(file);
      setFeedback(null);
    }
  };

  const getStatusBadge = (status: BulkImportStatusType) => {
    switch (status) {
      case "committed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle className="w-3 h-3 mr-1" />
            Committed
          </span>
        );
      case "validated":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
            <Info className="w-3 h-3 mr-1" />
            Validated (Dry Run)
          </span>
        );
      case "failed":
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            <XCircle className="w-3 h-3 mr-1" />
            Failed
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
            <Upload className="w-7 h-7 text-emerald-600" />
            {t("reports.bulkImportsTitle", "Bulk Data Importer")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "reports.bulkImportsSubtitle",
              "Batch import student directories and staff rosters via CSV with pre-validation dry-runs"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleDownloadTemplate()}
          className="inline-flex items-center justify-center px-4 py-2 border border-emerald-300 rounded-lg shadow-sm text-sm font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition"
        >
          <Download className="w-4 h-4 mr-2" />
          {t("reports.downloadTemplateBtn", "Download CSV Template")}
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

      {/* Target Selector Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            type="button"
            onClick={() => {
              setActiveTarget("students");
              setSelectedFile(null);
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTarget === "students"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Students Directory
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTarget("staff");
              setSelectedFile(null);
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTarget === "staff"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Staff & Faculty Roster
          </button>
        </nav>
      </div>

      {/* File Upload Box */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-base font-bold text-gray-900 mb-1">
          {t("reports.uploadCsvHeader", "Upload Batch CSV File")}
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          Columns required: {activeTarget === "students" ? "student_id, name_en, gender, dob, admission_date, emergency_contact" : "employee_id, full_name_en, gender, dob, phone, joining_date"}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          <div className="md:col-span-2 border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-emerald-400 transition bg-gray-50/50">
            <FileSpreadsheet className="w-10 h-10 text-gray-400 mx-auto mb-2" />
            <div className="text-sm text-gray-600 mb-2">
              <label htmlFor="csv_upload" className="font-semibold text-emerald-600 hover:text-emerald-700 cursor-pointer">
                Click to browse CSV
              </label>{" "}
              or drag and drop file here
            </div>
            <input
              id="csv_upload"
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
            {selectedFile ? (
              <span className="inline-block mt-2 font-mono text-xs font-semibold px-2.5 py-1 bg-emerald-100 text-emerald-900 rounded">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            ) : (
              <span className="text-xs text-gray-400 block">UTF-8 encoded comma-separated values (.csv)</span>
            )}
          </div>

          <div className="space-y-4">
            <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-xl border border-amber-200">
              <input
                id="dry_run_check"
                type="checkbox"
                checked={isDryRun}
                onChange={(e) => setIsDryRun(e.target.checked)}
                className="rounded text-emerald-600 focus:ring-emerald-500 h-4 w-4 mt-0.5"
              />
              <label htmlFor="dry_run_check" className="text-xs text-amber-900">
                <span className="font-bold block">Dry-Run Validation Only</span>
                Verifies format and checks for duplicates without writing to database.
              </label>
            </div>

            <button
              type="button"
              onClick={() => uploadMutation.mutate()}
              disabled={!selectedFile || uploadMutation.isPending}
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Upload className="w-4 h-4" />
              {uploadMutation.isPending
                ? t("common.saving", "Processing...")
                : isDryRun
                ? t("reports.validateNow", "Validate CSV File")
                : t("reports.commitNow", "Commit & Ingest Data")}
            </button>
          </div>
        </div>
      </div>

      {/* Batch Import History Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <h3 className="text-sm font-bold text-gray-900">
            {t("reports.importHistoryTitle", "Import Validation Logs & Status")}
          </h3>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading import history...")}</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-12 text-center">
            <FileSpreadsheet className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("reports.noImportsFound", "No Import Jobs on Record")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("reports.noImportsDesc", "Upload a CSV file to validate and bulk enroll institutional records.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("reports.target", "Target")}</th>
                  <th className="px-4 py-3">{t("reports.status", "Status")}</th>
                  <th className="px-3 py-3 text-center">{t("reports.totalRows", "Total Rows")}</th>
                  <th className="px-3 py-3 text-center">{t("reports.validRows", "Valid")}</th>
                  <th className="px-3 py-3 text-center">{t("reports.errorRows", "Errors")}</th>
                  <th className="px-4 py-3">{t("reports.uploadedAt", "Uploaded At")}</th>
                  <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50/75 transition">
                    <td className="px-5 py-3 font-semibold text-gray-900 capitalize text-xs">
                      {job.target_type}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {getStatusBadge(job.status)}
                    </td>
                    <td className="px-3 py-3 text-center font-mono text-xs font-bold text-gray-900">
                      {job.total_rows}
                    </td>
                    <td className="px-3 py-3 text-center font-mono text-xs font-bold text-emerald-700">
                      {job.valid_rows}
                    </td>
                    <td className="px-3 py-3 text-center font-mono text-xs font-bold text-rose-700">
                      {job.error_rows}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                      <div className="flex items-center gap-1 font-mono text-xs">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        {new Date(job.created_at).toLocaleString("en-BD", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedJob(job)}
                        className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" />
                        {t("reports.inspectValidation", "Inspect")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Inspection Breakdown */}
      <Dialog open={!!selectedJob} onOpenChange={(open) => { if (!open) setSelectedJob(null); }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto p-6">
          <DialogHeader className="border-b border-gray-200 pb-3">
            <DialogTitle className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
              {t("reports.validationModalTitle", "Import Analysis Breakdown")}
            </DialogTitle>
          </DialogHeader>

          {selectedJob && (
            <div className="space-y-4 text-xs pt-1">
              {/* Summary KPIs */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <span className="text-gray-500 text-xs block">Total Rows</span>
                  <span className="text-xl font-bold text-gray-900 font-mono mt-0.5 block">{selectedJob.total_rows}</span>
                </div>
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
                  <span className="text-emerald-700 text-xs block">Valid Rows</span>
                  <span className="text-xl font-bold text-emerald-800 font-mono mt-0.5 block">{selectedJob.valid_rows}</span>
                </div>
                <div className="p-3 bg-rose-50 rounded-xl border border-rose-200">
                  <span className="text-rose-700 text-xs block">Error Rows</span>
                  <span className="text-xl font-bold text-rose-800 font-mono mt-0.5 block">{selectedJob.error_rows}</span>
                </div>
              </div>

              {/* Errors Breakdown */}
              {selectedJob.errors_summary && selectedJob.errors_summary.length > 0 ? (
                <div>
                  <span className="font-semibold text-rose-700 flex items-center gap-1 mb-2">
                    <AlertTriangle className="w-4 h-4" />
                    Validation Errors ({selectedJob.errors_summary.length}):
                  </span>
                  <div className="border border-rose-200 rounded-xl overflow-hidden max-h-56 overflow-y-auto">
                    <table className="min-w-full divide-y divide-rose-200 text-left text-xs">
                      <thead className="bg-rose-50 text-rose-800 font-semibold uppercase">
                        <tr>
                          <th className="px-3 py-2 text-center">Row</th>
                          <th className="px-3 py-2">Field</th>
                          <th className="px-4 py-2">Error Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-rose-100 bg-white">
                        {selectedJob.errors_summary.map((err, idx) => (
                          <tr key={idx} className="hover:bg-rose-50/50">
                            <td className="px-3 py-2 text-center font-mono font-bold text-rose-900">
                              {err.row}
                            </td>
                            <td className="px-3 py-2 font-mono text-gray-700">
                              {err.field || "general"}
                            </td>
                            <td className="px-4 py-2 text-rose-800">
                              {err.error}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center text-emerald-800 font-medium">
                  <CheckCircle className="w-6 h-6 text-emerald-600 mx-auto mb-1" />
                  All rows passed validation with zero errors!
                </div>
              )}

              <div className="pt-4 border-t border-gray-200 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedJob(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
                >
                  {t("common.close", "Close")}
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
