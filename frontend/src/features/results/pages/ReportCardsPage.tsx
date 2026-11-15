import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  CheckCircle2,
  Eye,
  FileText,
  Search,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  resultsApi,
  type ExamResultItem,
} from "@/features/results/api/resultsApi";
import { examsApi } from "@/features/exams/api/examsApi";
import { academicApi } from "@/features/academics/api/academicApi";
import { ReportCardPreview } from "@/features/results/components/ReportCardPreview";

export default function ReportCardsPage() {
  const { t } = useTranslation();

  const [selectedExam, setSelectedExam] = useState<string>("");
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedSection, setSelectedSection] = useState<string>("");
  const [search, setSearch] = useState("");
  const [previewResult, setPreviewResult] = useState<ExamResultItem | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Queries
  const { data: examsData } = useQuery({
    queryKey: ["exams-list"],
    queryFn: () => examsApi.getExams(),
  });

  const { data: classesData = [] } = useQuery({
    queryKey: ["academic-classes"],
    queryFn: () => academicApi.getClasses(),
  });

  const { data: sectionsData = [] } = useQuery({
    queryKey: ["academic-sections", selectedClass],
    queryFn: () => academicApi.getSections(selectedClass || undefined),
    enabled: Boolean(selectedClass),
  });

  const { data: examResultsData, isLoading } = useQuery({
    queryKey: ["report-cards-results", selectedExam, search],
    queryFn: () =>
      resultsApi.getExamResults({
        exam: selectedExam || undefined,
        search: search.trim() || undefined,
      }),
    enabled: Boolean(selectedExam),
  });

  const { data: subjectResultsData } = useQuery({
    queryKey: ["preview-subject-results", previewResult?.id, selectedExam],
    queryFn: () =>
      resultsApi.getSubjectResults({
        exam: selectedExam,
        student: previewResult?.student,
      }),
    enabled: Boolean(previewResult) && Boolean(selectedExam),
  });

  const exams = useMemo(() => examsData?.results ?? [], [examsData]);
  const results = useMemo(() => examResultsData?.results ?? [], [examResultsData]);
  const subjectResults = useMemo(() => subjectResultsData?.results ?? [], [subjectResultsData]);

  // Bulk ZIP Mutation
  const bulkZipMutation = useMutation({
    mutationFn: () => {
      if (!selectedExam || !selectedClass) {
        throw new Error("Please select Exam and Class Grade.");
      }
      return resultsApi.bulkZipReportCards({
        exam_id: selectedExam,
        class_level_id: selectedClass,
        section_id: selectedSection || undefined,
      });
    },
    onSuccess: () => {
      setNotification({
        message: "Report cards bulk generation queued successfully.",
        type: "success",
      });
    },
    onError: (err: unknown) => {
      setNotification({
        message: err instanceof Error ? err.message : "Bulk generation failed.",
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
              {t("results.reportCardsTitle", "Student Progress Report Cards")}
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t(
              "results.reportCardsSubtitle",
              "Generate, preview, and batch-export official NCTB GPA 5.0 academic progress transcripts."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            disabled={!selectedExam || !selectedClass || bulkZipMutation.isPending}
            onClick={() => bulkZipMutation.mutate()}
            className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
          >
            <Archive className="h-3.5 w-3.5" />
            {bulkZipMutation.isPending ? "Generating..." : "Download Class ZIP"}
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

      {/* Filter Ribbon */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label htmlFor="report-exam-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Exam Cycle *</label>
            <select
              id="report-exam-select"
              value={selectedExam}
              onChange={(e) => setSelectedExam(e.target.value)}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">Select Examination...</option>
              {exams.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.name} ({ex.session_name})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="report-class-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Class Grade</label>
            <select
              id="report-class-select"
              value={selectedClass}
              onChange={(e) => {
                setSelectedClass(e.target.value);
                setSelectedSection("");
              }}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">All Classes</option>
              {classesData.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="report-section-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Section</label>
            <select
              id="report-section-select"
              value={selectedSection}
              disabled={!selectedClass}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50"
            >
              <option value="">All Sections</option>
              {sectionsData.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Roster & Search */}
      {!selectedExam ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          <FileText className="mx-auto mb-2 h-8 w-8 text-slate-300" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">Select an Exam Cycle above</p>
          <p className="mt-1 text-slate-400">Preview and print individual student transcripts or batch download PDF bundles.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search candidate name or code..."
              className="h-8 pl-8 text-xs"
            />
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {isLoading ? (
              <div className="p-12 text-center text-xs text-slate-500">Loading student results...</div>
            ) : results.length === 0 ? (
              <div className="p-12 text-center text-xs text-slate-500">
                No results tabulated for this examination.
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
                      <th className="px-3 py-2.5 font-semibold text-center">Final GPA</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Grade</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Merit</th>
                      <th className="px-4 py-2.5 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {results.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-3 py-2 text-center font-mono font-bold">{r.roll_no}</td>
                        <td className="px-4 py-2">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">{r.student_name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">{r.student_code}</div>
                        </td>
                        <td className="px-4 py-2 text-slate-600 dark:text-slate-400">
                          {r.class_level_name} ({r.section_name})
                        </td>
                        <td className="px-3 py-2 text-center font-mono font-semibold">{r.total_marks || "0"}</td>
                        <td className="px-3 py-2 text-center font-mono font-extrabold text-slate-900 dark:text-slate-100">
                          {r.final_gpa || "0.00"}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span
                            className={`px-1.5 py-0.5 rounded-sm text-[10px] font-bold ${
                              r.final_grade === "A+"
                                ? "bg-emerald-100 text-emerald-800"
                                : r.final_grade === "F"
                                ? "bg-rose-100 text-rose-800"
                                : "bg-blue-100 text-blue-800"
                            }`}
                          >
                            {r.final_grade}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center font-mono font-bold">#{r.class_position || "-"}</td>
                        <td className="px-4 py-2 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPreviewResult(r)}
                            className="h-7 gap-1 px-2.5 text-xs text-emerald-800 border-emerald-300"
                          >
                            <Eye className="h-3 w-3" />
                            View Transcript
                          </Button>
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

      {/* Modal: Report Card Preview */}
      {previewResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 max-h-[90vh] overflow-y-auto">
            <ReportCardPreview
              result={previewResult}
              subjectResults={subjectResults}
              onClose={() => setPreviewResult(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
