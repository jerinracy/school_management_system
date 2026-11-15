import { useState, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  Award,
  CheckCircle2,
  FileCheck2,
  FileSpreadsheet,
  FileText,
  Play,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Sliders,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { resultsApi } from "@/features/results/api/resultsApi";
import { examsApi } from "@/features/exams/api/examsApi";

export default function ResultsDashboardPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const examParam = searchParams.get("exam") || "";
  const [selectedExam, setSelectedExam] = useState<string>(examParam);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Queries
  const { data: examsData } = useQuery({
    queryKey: ["exams-list"],
    queryFn: () => examsApi.getExams(),
  });

  const { data: resultsData, isLoading } = useQuery({
    queryKey: ["exam-results-list", selectedExam, search],
    queryFn: () =>
      resultsApi.getExamResults({
        exam: selectedExam || undefined,
        search: search.trim() || undefined,
      }),
    enabled: Boolean(selectedExam),
  });

  const { data: summaryData } = useQuery({
    queryKey: ["exam-result-summary", selectedExam],
    queryFn: () => resultsApi.getExamResultSummary(selectedExam),
    enabled: Boolean(selectedExam),
  });

  const exams = useMemo(() => examsData?.results ?? [], [examsData]);
  const results = useMemo(() => resultsData?.results ?? [], [resultsData]);
  const summary = summaryData as {
    total_students?: number;
    passed_count?: number;
    failed_count?: number;
    pass_percentage?: number;
    average_gpa?: number;
    grade_distribution?: Record<string, number>;
  } | undefined;

  // Selected Exam object
  const currentExam = useMemo(() => exams.find((e) => e.id === selectedExam), [exams, selectedExam]);

  // Mutations
  const calculateMutation = useMutation({
    mutationFn: () => {
      if (!selectedExam) throw new Error("Please select an examination first.");
      return resultsApi.calculateExamResults(selectedExam);
    },
    onSuccess: (data: unknown) => {
      void queryClient.invalidateQueries({ queryKey: ["exam-results-list", selectedExam] });
      void queryClient.invalidateQueries({ queryKey: ["exam-result-summary", selectedExam] });
      setNotification({
        message: (data as { message?: string })?.message || "GPA 5.0 results tabulated and ranked successfully.",
        type: "success",
      });
    },
    onError: (err: unknown) => {
      setNotification({
        message: err instanceof Error ? err.message : "Result calculation failed.",
        type: "error",
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => resultsApi.approveResults(selectedExam, "Approved by Principal"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exams-list"] });
      setNotification({ message: "Examination results approved successfully.", type: "success" });
    },
  });

  const publishMutation = useMutation({
    mutationFn: (opts: { is_visible_to_guardians: boolean; is_visible_to_students: boolean; allow_public_search: boolean }) =>
      resultsApi.publishResults({
        exam_id: selectedExam,
        ...opts,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exams-list"] });
      setShowPublishModal(false);
      setNotification({ message: "Results published to student and guardian portals.", type: "success" });
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: () => resultsApi.unpublishResults(selectedExam),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exams-list"] });
      setNotification({ message: "Published results reverted back to draft.", type: "success" });
    },
  });

  // Filtered rows
  const filteredResults = useMemo(() => {
    if (statusFilter === "PASSED") return results.filter((r) => r.is_passed);
    if (statusFilter === "FAILED") return results.filter((r) => !r.is_passed);
    return results;
  }, [results, statusFilter]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("results.title", "Examination Results & GPA 5.0 Processing")}
            </h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              <Award className="h-3 w-3" />
              NCTB Engine
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t(
              "results.subtitle",
              "Execute Bangladeshi grading rules (combined papers, 4th subject GP benefit, failing F overrides) and formal publication."
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link to="/results/tabulation">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
              Tabulation Sheet
            </Button>
          </Link>
          <Link to="/results/report-cards">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
              <FileText className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
              Report Cards
            </Button>
          </Link>
          <Link to="/results/grading-scales">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
              <Sliders className="h-3.5 w-3.5" />
              Grading Scales
            </Button>
          </Link>
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

      {/* Exam Selector & Actions Ribbon */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <label htmlFor="results-exam-select" className="text-xs font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
            Active Exam Cycle:
          </label>
          <select
            id="results-exam-select"
            value={selectedExam}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedExam(val);
              setSearchParams(val ? { exam: val } : {});
            }}
            className="w-full sm:w-72 h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="">Select Examination Cycle...</option>
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name} ({ex.session_name})
              </option>
            ))}
          </select>
        </div>

        {selectedExam && (
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
            <Button
              size="sm"
              disabled={calculateMutation.isPending}
              onClick={() => calculateMutation.mutate()}
              className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
            >
              <Play className="h-3.5 w-3.5" />
              {calculateMutation.isPending ? "Tabulating..." : "Calculate GPA 5.0"}
            </Button>

            {currentExam?.status !== "published" ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={approveMutation.isPending}
                  onClick={() => approveMutation.mutate()}
                  className="h-9 gap-1.5 text-xs text-blue-700 border-blue-300 dark:border-blue-800 dark:text-blue-300"
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Approve Results
                </Button>
                <Button
                  size="sm"
                  onClick={() => setShowPublishModal(true)}
                  className="h-9 gap-1.5 text-xs bg-emerald-700 text-white hover:bg-emerald-800"
                >
                  <Send className="h-3.5 w-3.5" />
                  Publish Results
                </Button>
              </>
            ) : (
              <Button
                variant="outline"
                size="sm"
                disabled={unpublishMutation.isPending}
                onClick={() => unpublishMutation.mutate()}
                className="h-9 gap-1.5 text-xs text-amber-700 border-amber-300"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Unpublish to Draft
              </Button>
            )}
          </div>
        )}
      </div>

      {/* KPI & Grade Distribution Banner */}
      {selectedExam && summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 md:col-span-1">
            <span className="text-xs font-medium text-slate-500">Overall Performance</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-emerald-700 dark:text-emerald-300">
                {summary.pass_percentage ?? 0}%
              </span>
              <span className="text-xs text-slate-500">Pass Rate</span>
            </div>
            <div className="mt-3 text-[11px] text-slate-500 space-y-1">
              <div>Total Evaluated: <span className="font-semibold text-slate-700 dark:text-slate-300">{summary.total_students}</span></div>
              <div>Passed: <span className="font-semibold text-emerald-600">{summary.passed_count}</span> | Failed: <span className="font-semibold text-rose-600">{summary.failed_count}</span></div>
              <div>Average GPA: <span className="font-semibold text-slate-900 dark:text-slate-100">{summary.average_gpa?.toFixed(2)}</span> / 5.00</div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 md:col-span-3">
            <span className="text-xs font-medium text-slate-500">Grade Point Distribution (NCTB GPA 5.0)</span>
            <div className="mt-3 grid grid-cols-7 gap-2 text-center text-xs">
              {["A+", "A", "A-", "B", "C", "D", "F"].map((grade) => {
                const count = summary.grade_distribution?.[grade] || 0;
                return (
                  <div
                    key={grade}
                    className={`rounded-lg p-2.5 border ${
                      grade === "A+"
                        ? "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800"
                        : grade === "F"
                        ? "bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-800"
                        : "bg-slate-50 border-slate-200 dark:bg-slate-800/40 dark:border-slate-700"
                    }`}
                  >
                    <div className="font-extrabold text-slate-900 dark:text-slate-100 text-sm">{grade}</div>
                    <div className="mt-1 font-mono font-bold text-slate-700 dark:text-slate-300">{count}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Results Table */}
      {!selectedExam ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          <Award className="mx-auto mb-2 h-8 w-8 text-slate-300" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">Select an Examination Cycle above</p>
          <p className="mt-1 text-slate-400">View tabulated results, compute merit positions, or generate report cards.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Table Filters */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search candidate name or code..."
                className="h-8 pl-8 text-xs"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
              >
                <option value="ALL">All Outcomes</option>
                <option value="PASSED">Passed Only</option>
                <option value="FAILED">Failed Only</option>
              </select>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {isLoading ? (
              <div className="p-12 text-center text-xs text-slate-500">Loading student results...</div>
            ) : filteredResults.length === 0 ? (
              <div className="p-12 text-center text-xs text-slate-500">
                <FileCheck2 className="mx-auto mb-2 h-8 w-8 text-slate-300" />
                <p className="font-semibold text-slate-700 dark:text-slate-300">No student results tabulated</p>
                <p className="mt-1 text-slate-400">Click &quot;Calculate GPA 5.0&quot; to execute result processing.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-2.5 font-semibold text-center w-12">Roll</th>
                      <th className="px-4 py-2.5 font-semibold">Candidate Student</th>
                      <th className="px-4 py-2.5 font-semibold">Class & Section</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Marks</th>
                      <th className="px-3 py-2.5 font-semibold text-center">GPA (w/o 4th)</th>
                      <th className="px-3 py-2.5 font-semibold text-center">4th Bonus</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Final GPA</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Grade</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Rank</th>
                      <th className="px-4 py-2.5 font-semibold text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {filteredResults.map((res) => (
                      <tr key={res.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-3 py-2 text-center font-mono font-semibold">{res.roll_no}</td>
                        <td className="px-4 py-2">
                          <div className="font-medium text-slate-900 dark:text-slate-100">{res.student_name}</div>
                          <div className="text-[11px] text-slate-400 font-mono">{res.student_code}</div>
                        </td>
                        <td className="px-4 py-2 text-slate-600 dark:text-slate-400">
                          {res.class_level_name} ({res.section_name})
                        </td>
                        <td className="px-3 py-2 text-center font-mono font-semibold">
                          {res.total_marks || "0"}
                        </td>
                        <td className="px-3 py-2 text-center font-mono text-slate-600 dark:text-slate-400">
                          {res.gpa_without_fourth || "0.00"}
                        </td>
                        <td className="px-3 py-2 text-center font-mono text-emerald-700 dark:text-emerald-400">
                          +{res.fourth_subject_bonus || "0.00"}
                        </td>
                        <td className="px-3 py-2 text-center font-mono font-extrabold text-slate-900 dark:text-slate-100">
                          {res.final_gpa || "0.00"}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span
                            className={`inline-block rounded-sm px-1.5 py-0.5 text-[10px] font-bold ${
                              res.final_grade === "A+"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : res.final_grade === "F"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                                : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                            }`}
                          >
                            {res.final_grade}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center font-mono font-bold text-slate-700 dark:text-slate-300">
                          #{res.class_position || "-"}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <span
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                              res.is_passed
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                            }`}
                          >
                            {res.is_passed ? "Passed" : "Failed"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Publish Results */}
      {showPublishModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Formally Publish Examination Results
              </h2>
              <button onClick={() => setShowPublishModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              Publishing will release official GPA 5.0 marks to student and parent mobile portals.
            </p>

            <div className="space-y-2.5 text-xs">
              <label className="flex items-center gap-2">
                <input type="checkbox" defaultChecked id="pub-guardians" className="h-4 w-4 rounded-sm border-slate-300 text-emerald-800" />
                <span>Visible to Parents / Guardians on Portal</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" defaultChecked id="pub-students" className="h-4 w-4 rounded-sm border-slate-300 text-emerald-800" />
                <span>Visible to Enrolled Students on Portal</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" id="pub-public" className="h-4 w-4 rounded-sm border-slate-300 text-emerald-800" />
                <span>Enable Public Search by Roll & Registration</span>
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <Button variant="outline" size="sm" onClick={() => setShowPublishModal(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="sm"
                disabled={publishMutation.isPending}
                onClick={() => {
                  const g = (document.getElementById("pub-guardians") as HTMLInputElement)?.checked ?? true;
                  const s = (document.getElementById("pub-students") as HTMLInputElement)?.checked ?? true;
                  const p = (document.getElementById("pub-public") as HTMLInputElement)?.checked ?? false;
                  publishMutation.mutate({
                    is_visible_to_guardians: g,
                    is_visible_to_students: s,
                    allow_public_search: p,
                  });
                }}
                className="bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {publishMutation.isPending ? "Publishing..." : "Confirm & Publish"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
