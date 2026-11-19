import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FileSpreadsheet,
  Plus,
  Download,
  Share2,
  Lock,
  Layers,
  CheckCircle,
} from "lucide-react";
import {
  reportsApi,
  DATASET_SPEC,
  type ReportDatasetType,
  type ExportFormatType,
} from "../api/reportsApi";
import {
  reportDefinitionSchema,
  type ReportDefinitionFormData,
} from "../schemas/reportsSchemas";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const ReportDefinitionsPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selectedDatasetFilter, setSelectedDatasetFilter] = useState<string>("all");
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch report definitions
  const { data: definitionsData, isLoading } = useQuery({
    queryKey: ["report-definitions", selectedDatasetFilter],
    queryFn: () =>
      reportsApi.getReportDefinitions({
        dataset: selectedDatasetFilter !== "all" ? selectedDatasetFilter : undefined,
      }),
  });

  const definitions = definitionsData?.results || [];

  // Export from definition mutation
  const exportMutation = useMutation({
    mutationFn: (id: string) => reportsApi.exportReportDefinition(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["report-exports"] });
      setFeedback({
        type: "success",
        message: t("reports.exportQueuedSuccess", "Report export queued successfully. View in Export History."),
      });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  // Create definition form
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ReportDefinitionFormData>({
    resolver: zodResolver(reportDefinitionSchema) as never,
    defaultValues: {
      name: "",
      dataset: "students",
      selected_columns: ["student_id", "name_en", "gender", "status"],
      default_format: "csv",
      is_shared: false,
    },
  });

  const selectedDataset = watch("dataset");
  const selectedColumns = watch("selected_columns") || [];

  const handleDatasetChange = (ds: ReportDatasetType) => {
    setValue("dataset", ds);
    const initialCols = DATASET_SPEC[ds].columns.slice(0, 4).map((c) => c.key);
    setValue("selected_columns", initialCols);
  };

  const handleColumnToggle = (colKey: string) => {
    if (selectedColumns.includes(colKey)) {
      if (selectedColumns.length > 1) {
        setValue(
          "selected_columns",
          selectedColumns.filter((c) => c !== colKey)
        );
      }
    } else {
      setValue("selected_columns", [...selectedColumns, colKey]);
    }
  };

  const createMutation = useMutation({
    mutationFn: (data: ReportDefinitionFormData) =>
      reportsApi.createReportDefinition(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["report-definitions"] });
      setIsCreateOpen(false);
      reset();
      setFeedback({
        type: "success",
        message: t("reports.definitionCreatedSuccess", "Report definition saved successfully"),
      });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const onSubmit = (data: ReportDefinitionFormData) => {
    createMutation.mutate(data);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <FileSpreadsheet className="w-7 h-7 text-emerald-600" />
            {t("reports.reportDefinitionsTitle", "Dynamic Report Builder")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "reports.reportDefinitionsSubtitle",
              "Construct custom data extracts across students, attendance, fee collections, and examinations"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsCreateOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("reports.newDefinitionBtn", "Create Report Query")}
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

      {/* Dataset Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setSelectedDatasetFilter("all")}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
            selectedDatasetFilter === "all"
              ? "bg-emerald-600 text-white shadow-sm"
              : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
          }`}
        >
          {t("common.allDatasets", "All Datasets")} ({definitions.length})
        </button>
        {Object.entries(DATASET_SPEC).map(([key, spec]) => (
          <button
            key={key}
            type="button"
            onClick={() => setSelectedDatasetFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              selectedDatasetFilter === key
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {spec.label}
          </button>
        ))}
      </div>

      {/* Report Definitions List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {isLoading ? (
          <div className="col-span-full p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading saved report queries...")}</p>
          </div>
        ) : definitions.length === 0 ? (
          <div className="col-span-full p-12 text-center border rounded-xl bg-white">
            <Layers className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("reports.noDefinitionsFound", "No Report Definitions Saved")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("reports.noDefinitionsDesc", "Create saved report configurations with selected columns and filters for instant exports.")}
            </p>
          </div>
        ) : (
          definitions.map((def) => {
            const spec = DATASET_SPEC[def.dataset];

            return (
              <div
                key={def.id}
                className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col justify-between hover:border-emerald-300 transition"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                      {spec?.label || def.dataset}
                    </span>
                    <span className="font-mono text-xs font-bold uppercase px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                      {def.default_format}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-gray-900 mb-1">{def.name}</h3>

                  <div className="mt-3">
                    <span className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">
                      Columns ({def.selected_columns.length}):
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {def.selected_columns.slice(0, 4).map((col) => (
                        <span
                          key={col}
                          className="px-2 py-0.5 rounded bg-gray-50 border border-gray-200 text-gray-700 text-[11px] font-mono"
                        >
                          {col}
                        </span>
                      ))}
                      {def.selected_columns.length > 4 && (
                        <span className="text-[11px] text-gray-400 self-center">
                          +{def.selected_columns.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-100 mt-4 flex items-center justify-between">
                  <div className="flex items-center text-xs text-gray-500 gap-1">
                    {def.is_shared ? (
                      <>
                        <Share2 className="w-3.5 h-3.5 text-blue-600" />
                        <span>Shared</span>
                      </>
                    ) : (
                      <>
                        <Lock className="w-3.5 h-3.5 text-gray-400" />
                        <span>Private</span>
                      </>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => exportMutation.mutate(def.id)}
                    disabled={exportMutation.isPending}
                    className="inline-flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition disabled:opacity-50"
                  >
                    <Download className="w-3.5 h-3.5 mr-1" />
                    {t("reports.exportNow", "Export Now")}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal: Create Report Definition */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto p-6">
          <DialogHeader className="border-b border-gray-200 pb-3">
            <DialogTitle className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
              {t("reports.createDefinitionModalTitle", "Configure Report Definition")}
            </DialogTitle>
          </DialogHeader>

          <form
            onSubmit={(e) => {
              void handleSubmit(onSubmit)(e);
            }}
            className="space-y-4 pt-1"
          >
              {/* Name */}
              <div>
                <label htmlFor="def_name" className="block text-xs font-semibold text-gray-700 mb-1">
                  Report Title *
                </label>
                <input
                  id="def_name"
                  type="text"
                  placeholder="e.g. Monthly Class 10 Tuition Collections"
                  {...register("name")}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
              </div>

              {/* Dataset Selection */}
              <div>
                <label htmlFor="def_dataset" className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Dataset *
                </label>
                <select
                  id="def_dataset"
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
                  Selected Columns ({selectedColumns.length}) *
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-3 bg-gray-50 rounded-xl border border-gray-200 max-h-48 overflow-y-auto">
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
                {errors.selected_columns && (
                  <p className="text-xs text-red-600 mt-1">{errors.selected_columns.message}</p>
                )}
              </div>

              {/* Default Export Format */}
              <div>
                <span className="block text-xs font-semibold text-gray-700 mb-1">
                  Default Export Format *
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
                        {...register("default_format")}
                        className="text-emerald-600 focus:ring-emerald-500"
                      />
                      <span>{fmt}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Shared Visibility Toggle */}
              <div className="flex items-center gap-2 pt-2">
                <input
                  id="is_shared"
                  type="checkbox"
                  {...register("is_shared")}
                  className="rounded text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                />
                <label htmlFor="is_shared" className="text-xs text-gray-700 font-medium">
                  Share this report query with other institutional administrators
                </label>
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || createMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || createMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("common.create", "Save Report Query")}
                </button>
              </div>
            </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
