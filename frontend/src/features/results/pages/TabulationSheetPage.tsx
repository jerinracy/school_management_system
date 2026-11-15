import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Printer,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { resultsApi } from "@/features/results/api/resultsApi";
import { examsApi } from "@/features/exams/api/examsApi";
import { academicApi } from "@/features/academics/api/academicApi";

export default function TabulationSheetPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selectedExam, setSelectedExam] = useState<string>("");
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedSection, setSelectedSection] = useState<string>("");
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

  const { data: sheetsData } = useQuery({
    queryKey: ["tabulation-sheets", selectedExam, selectedClass],
    queryFn: () =>
      resultsApi.getTabulationSheets({
        exam: selectedExam || undefined,
        class_level: selectedClass || undefined,
      }),
  });

  const { data: examResultsData } = useQuery({
    queryKey: ["tabulation-results", selectedExam, selectedClass],
    queryFn: () =>
      resultsApi.getExamResults({
        exam: selectedExam || undefined,
        class_level: selectedClass || undefined,
      }),
    enabled: Boolean(selectedExam) && Boolean(selectedClass),
  });

  const exams = useMemo(() => examsData?.results ?? [], [examsData]);
  const sheets = useMemo(() => sheetsData?.results ?? [], [sheetsData]);
  const results = useMemo(() => examResultsData?.results ?? [], [examResultsData]);

  // Generate Tabulation Sheet Mutation
  const generateSheetMutation = useMutation({
    mutationFn: (format: "pdf" | "excel" | "csv") => {
      if (!selectedExam || !selectedClass) {
        throw new Error("Please select both Exam and Class Grade.");
      }
      return resultsApi.createTabulationSheet({
        exam: selectedExam,
        class_level: selectedClass,
        section: selectedSection || undefined,
        file_format: format,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tabulation-sheets"] });
      setNotification({
        message: "Tabulation Sheet generated successfully.",
        type: "success",
      });
    },
    onError: (err: unknown) => {
      setNotification({
        message: err instanceof Error ? err.message : "Failed to generate Tabulation Sheet.",
        type: "error",
      });
    },
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800 print:hidden">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/results" className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("results.tabulationTitle", "Official Tabulation Sheet Register")}
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t(
              "results.tabulationSubtitle",
              "Master board-standard broadsheet detailing subject CQ/MCQ/PR breakdowns, GPAs, and class merit positions."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.print()}
            className="h-9 gap-1.5 text-xs"
          >
            <Printer className="h-3.5 w-3.5" />
            Print Broadsheet
          </Button>
          <Button
            size="sm"
            disabled={!selectedExam || !selectedClass || generateSheetMutation.isPending}
            onClick={() => generateSheetMutation.mutate("pdf")}
            className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            {generateSheetMutation.isPending ? "Generating..." : "Generate Official Sheet"}
          </Button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`flex items-center justify-between rounded-xl p-3 text-xs print:hidden ${
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

      {/* Selector Ribbon */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 print:hidden">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label htmlFor="tab-exam-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Exam Cycle *</label>
            <select
              id="tab-exam-select"
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
            <label htmlFor="tab-class-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Class Grade *</label>
            <select
              id="tab-class-select"
              value={selectedClass}
              disabled={!selectedExam}
              onChange={(e) => {
                setSelectedClass(e.target.value);
                setSelectedSection("");
              }}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50"
            >
              <option value="">Select Class...</option>
              {classesData.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="tab-section-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Section</label>
            <select
              id="tab-section-select"
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

      {/* Broadsheet Container */}
      {!selectedExam || !selectedClass ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900 print:hidden">
          <FileSpreadsheet className="mx-auto mb-2 h-8 w-8 text-slate-300" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">Select Exam and Class Grade above</p>
          <p className="mt-1 text-slate-400">View official board tabulation register with rankings and breakdowns.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Institutional Broadsheet Header (Visible on print & screen) */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900 print:border-none print:shadow-none print:p-0">
            <div className="text-center border-b pb-4 mb-4 border-slate-200 dark:border-slate-800">
              <h2 className="text-base font-extrabold uppercase tracking-wide text-slate-900 dark:text-slate-100">
                Dhaka Model High School &amp; College
              </h2>
              <p className="text-xs text-slate-500">
                EIIN: 134567 &bull; Dhaka Education Board &bull; Bangladesh
              </p>
              <div className="mt-1 font-bold text-emerald-800 dark:text-emerald-400 text-sm">
                Official Examination Tabulation Sheet (NCTB GPA 5.0)
              </div>
            </div>

            {/* Results Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="border-b-2 border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-950 text-slate-700 dark:text-slate-300">
                  <tr>
                    <th className="px-3 py-2 text-center w-12 font-bold">Roll</th>
                    <th className="px-4 py-2 font-bold">Candidate Name</th>
                    <th className="px-3 py-2 font-bold">Section</th>
                    <th className="px-3 py-2 text-center font-bold">Total Marks</th>
                    <th className="px-3 py-2 text-center font-bold">GPA (Base)</th>
                    <th className="px-3 py-2 text-center font-bold">4th Bonus</th>
                    <th className="px-3 py-2 text-center font-bold">Final GPA</th>
                    <th className="px-3 py-2 text-center font-bold">Grade</th>
                    <th className="px-3 py-2 text-center font-bold">Class Rank</th>
                    <th className="px-3 py-2 text-center font-bold">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {results.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-slate-500">
                        No tabulated records found. Run GPA calculation in Results Dashboard.
                      </td>
                    </tr>
                  ) : (
                    results.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-3 py-2 text-center font-mono font-bold">{r.roll_no}</td>
                        <td className="px-4 py-2">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">{r.student_name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">{r.student_code}</div>
                        </td>
                        <td className="px-3 py-2 text-slate-600 dark:text-slate-400">{r.section_name}</td>
                        <td className="px-3 py-2 text-center font-mono font-semibold">{r.total_marks || "0"}</td>
                        <td className="px-3 py-2 text-center font-mono">{r.gpa_without_fourth || "0.00"}</td>
                        <td className="px-3 py-2 text-center font-mono text-emerald-700">+{r.fourth_subject_bonus || "0.00"}</td>
                        <td className="px-3 py-2 text-center font-mono font-extrabold text-slate-900 dark:text-slate-100">
                          {r.final_gpa || "0.00"}
                        </td>
                        <td className="px-3 py-2 text-center font-bold">
                          <span
                            className={`px-1.5 py-0.5 rounded-sm text-[10px] ${
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
                        <td className="px-3 py-2 text-center">
                          <span
                            className={`font-bold text-[10px] uppercase ${
                              r.is_passed ? "text-emerald-700" : "text-rose-600"
                            }`}
                          >
                            {r.is_passed ? "Passed" : "Failed"}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Print Signatures */}
            <div className="hidden print:flex justify-between items-end pt-16 text-xs text-slate-800">
              <div className="text-center">
                <div className="border-t border-slate-500 w-36 pt-1 font-semibold">Prepared By</div>
              </div>
              <div className="text-center">
                <div className="border-t border-slate-500 w-36 pt-1 font-semibold">Verified By</div>
              </div>
              <div className="text-center">
                <div className="border-t border-slate-500 w-36 pt-1 font-semibold">Exam Controller</div>
              </div>
              <div className="text-center">
                <div className="border-t border-slate-500 w-36 pt-1 font-semibold">Principal</div>
              </div>
            </div>
          </div>

          {/* Generated Documents Archive */}
          {sheets.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 print:hidden space-y-3">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                Generated Archival Downloads
              </h3>
              <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {sheets.map((s) => (
                  <div key={s.id} className="flex items-center justify-between py-2">
                    <div>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {s.exam_name} &bull; {s.class_level_name} ({s.section_name})
                      </span>
                      <span className="ml-2 font-mono text-[11px] text-slate-400">
                        v{s.version} &bull; {s.generated_at?.slice(0, 10)}
                      </span>
                    </div>
                    {s.download_url && (
                      <a href={s.download_url} target="_blank" rel="noreferrer">
                        <Button variant="outline" size="sm" className="h-7 gap-1 text-xs text-emerald-800">
                          <Download className="h-3 w-3" />
                          Download ({s.file_format?.toUpperCase()})
                        </Button>
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
