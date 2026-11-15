import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Sliders,
  Sparkles,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { resultsApi } from "@/features/results/api/resultsApi";

export default function GradingScalesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const { data: scales = [], isLoading } = useQuery({
    queryKey: ["grading-scales-list"],
    queryFn: () => resultsApi.getGradingScales(),
  });

  const seedDefaultsMutation = useMutation({
    mutationFn: () => resultsApi.seedBdDefaults(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["grading-scales-list"] });
      setNotification({
        message: "Bangladesh NCTB standard grading scales initialized successfully.",
        type: "success",
      });
    },
    onError: (err: unknown) => {
      setNotification({
        message: err instanceof Error ? err.message : "Failed to seed grading scales.",
        type: "error",
      });
    },
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/results" className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("results.gradingScalesTitle", "Curriculum Grading Scales (GPA 5.0)")}
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t(
              "results.gradingScalesSubtitle",
              "Government Education Board and NCTB compliant grade tier allocations and GPA mapping."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            disabled={seedDefaultsMutation.isPending}
            onClick={() => seedDefaultsMutation.mutate()}
            className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {seedDefaultsMutation.isPending ? "Seeding..." : "Seed NCTB Defaults"}
          </Button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`flex items-center justify-between rounded-xl p-3 text-xs ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
              : "bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Scales List */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-500">Loading grading scales...</div>
      ) : scales.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          <Sliders className="mx-auto mb-2 h-8 w-8 text-slate-300" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">No grading scales found</p>
          <p className="mt-1 text-slate-400">Click &quot;Seed NCTB Defaults&quot; above to initialize Bangladeshi standard scales.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {scales.map((scale) => (
            <div
              key={scale.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-4"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{scale.name}</h2>
                    {scale.is_default && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        Default System Scale
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">{scale.description || "NCTB Secondary GPA 5.0 Standard"}</p>
                </div>
                <div className="text-right text-xs">
                  <div className="font-bold text-slate-900 dark:text-slate-100">Max GPA: {scale.max_gpa || "5.00"}</div>
                  <div className="text-slate-500">Passing GPA: {scale.pass_gpa || "1.00"}</div>
                </div>
              </div>

              {/* Tiers Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-2.5 font-semibold">Letter Grade</th>
                      <th className="px-4 py-2.5 font-semibold">Grade Point (GP)</th>
                      <th className="px-4 py-2.5 font-semibold">Score Range (%)</th>
                      <th className="px-4 py-2.5 font-semibold">Performance Remarks</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {(scale.tiers || []).map((t, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-2 font-bold">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-sm text-[11px] font-extrabold ${
                              t.letter_grade === "A+"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : t.letter_grade === "F"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                                : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                            }`}
                          >
                            {t.letter_grade}
                          </span>
                        </td>
                        <td className="px-4 py-2 font-mono font-bold text-slate-900 dark:text-slate-100">
                          {t.grade_point}
                        </td>
                        <td className="px-4 py-2 font-mono text-slate-600 dark:text-slate-400">
                          {t.min_percentage}% - {t.max_percentage}%
                        </td>
                        <td className="px-4 py-2 text-slate-600 dark:text-slate-400">
                          {t.remarks_en || t.remarks_bn || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
