import { useState, useMemo, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileCheck2,
  Lock,
  Save,
  Search,
  ShieldAlert,
  Unlock,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { examsApi, type MarkEntryItem, type ExamSubjectItem } from "@/features/exams/api/examsApi";
import { studentsApi } from "@/features/students/api/studentsApi";
import { academicApi } from "@/features/academics/api/academicApi";

// BD NCTB GPA 5.0 Grade Calculator
export function calculateBdGrade(
  total: number,
  fullMarks: number,
  cq: number,
  cqPass: number,
  mcq: number,
  mcqPass: number,
  isAbsent: boolean
): { grade: string; gp: number; isPassed: boolean; reason?: string } {
  if (isAbsent) {
    return { grade: "ABS", gp: 0.0, isPassed: false, reason: "Absent" };
  }
  if (cqPass > 0 && cq < cqPass) {
    return { grade: "F", gp: 0.0, isPassed: false, reason: "Failed in CQ" };
  }
  if (mcqPass > 0 && mcq < mcqPass) {
    return { grade: "F", gp: 0.0, isPassed: false, reason: "Failed in MCQ" };
  }

  const percentage = fullMarks > 0 ? (total / fullMarks) * 100 : 0;

  if (percentage >= 80) return { grade: "A+", gp: 5.0, isPassed: true };
  if (percentage >= 70) return { grade: "A", gp: 4.0, isPassed: true };
  if (percentage >= 60) return { grade: "A-", gp: 3.5, isPassed: true };
  if (percentage >= 50) return { grade: "B", gp: 3.0, isPassed: true };
  if (percentage >= 40) return { grade: "C", gp: 2.0, isPassed: true };
  if (percentage >= 33) return { grade: "D", gp: 1.0, isPassed: true };
  return { grade: "F", gp: 0.0, isPassed: false, reason: "Score below 33%" };
}

interface StudentRowState {
  student_id: string;
  roll_no?: number | string;
  name: string;
  code: string;
  cq: string;
  mcq: string;
  practical: string;
  is_absent: boolean;
}

export default function MarkEntryPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const examParam = searchParams.get("exam") || "";
  const subjectParam = searchParams.get("subject") || "";
  const classParam = searchParams.get("class") || "";
  const sectionParam = searchParams.get("section") || "";

  const [selectedExam, setSelectedExam] = useState<string>(examParam);
  const [selectedClass, setSelectedClass] = useState<string>(classParam);
  const [selectedSection, setSelectedSection] = useState<string>(sectionParam);
  const [selectedSubject, setSelectedSubject] = useState<string>(subjectParam);
  const [searchQuery, setSearchQuery] = useState("");

  const [marksState, setMarksState] = useState<Record<string, StudentRowState>>({});
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

  const { data: examSubjectsData } = useQuery({
    queryKey: ["exam-subjects", selectedExam, selectedClass],
    queryFn: () =>
      examsApi.getExamSubjects({
        exam: selectedExam || undefined,
        class_level: selectedClass || undefined,
      }),
    enabled: Boolean(selectedExam),
  });

  const { data: studentsData, isLoading: isStudentsLoading } = useQuery({
    queryKey: ["students-for-marks", selectedSection],
    queryFn: () => studentsApi.getStudents({ status: "active" }),
    enabled: Boolean(selectedSection),
  });

  const { data: existingMarksData } = useQuery({
    queryKey: ["existing-mark-entries", selectedSubject],
    queryFn: () => examsApi.getMarkEntries({ exam_subject: selectedSubject }),
    enabled: Boolean(selectedSubject),
  });

  const exams = useMemo(() => examsData?.results ?? [], [examsData]);
  const examSubjects = useMemo(() => examSubjectsData?.results ?? [], [examSubjectsData]);
  const students = useMemo(() => studentsData?.results ?? [], [studentsData]);
  const existingMarks = useMemo(() => existingMarksData?.results ?? [], [existingMarksData]);

  // Current active subject definition
  const currentSubject = useMemo<ExamSubjectItem | undefined>(() => {
    return examSubjects.find((s) => s.id === selectedSubject);
  }, [examSubjects, selectedSubject]);

  // Sync state when students or existing marks load
  useEffect(() => {
    if (students.length === 0) return;

    const existingMap = new Map<string, MarkEntryItem>();
    existingMarks.forEach((m) => existingMap.set(m.student, m));

    const initial: Record<string, StudentRowState> = {};
    students.forEach((s, idx) => {
      const match = existingMap.get(s.id);
      initial[s.id] = {
        student_id: s.id,
        roll_no: idx + 1,
        name: s.name_en,
        code: s.student_id,
        cq: match?.creative_marks ? String(match.creative_marks) : "",
        mcq: match?.mcq_marks ? String(match.mcq_marks) : "",
        practical: match?.practical_marks ? String(match.practical_marks) : "",
        is_absent: Boolean(match?.is_absent),
      };
    });
    setMarksState(initial);
  }, [students, existingMarks]);

  // Update URL search parameters
  const updateParams = (updates: { exam?: string; class?: string; section?: string; subject?: string }) => {
    const next = new URLSearchParams(searchParams);
    if (updates.exam !== undefined) {
      if (updates.exam) next.set("exam", updates.exam);
      else next.delete("exam");
    }
    if (updates.class !== undefined) {
      if (updates.class) next.set("class", updates.class);
      else next.delete("class");
    }
    if (updates.section !== undefined) {
      if (updates.section) next.set("section", updates.section);
      else next.delete("section");
    }
    if (updates.subject !== undefined) {
      if (updates.subject) next.set("subject", updates.subject);
      else next.delete("subject");
    }
    setSearchParams(next);
  };

  // Bulk Save Mutation
  const saveMarksMutation = useMutation({
    mutationFn: () => {
      if (!selectedSubject) throw new Error("No exam subject selected");
      const entries = Object.values(marksState).map((row) => ({
        student_id: row.student_id,
        creative_marks: row.is_absent || !row.cq ? null : parseFloat(row.cq),
        mcq_marks: row.is_absent || !row.mcq ? null : parseFloat(row.mcq),
        practical_marks: row.is_absent || !row.practical ? null : parseFloat(row.practical),
        is_absent: row.is_absent,
      }));
      return examsApi.bulkSaveMarks({
        exam_subject_id: selectedSubject,
        entries,
      });
    },
    onSuccess: (data: unknown) => {
      void queryClient.invalidateQueries({ queryKey: ["existing-mark-entries", selectedSubject] });
      setNotification({
        message: (data as { message?: string })?.message || "Marks saved successfully.",
        type: "success",
      });
    },
    onError: (err: unknown) => {
      setNotification({
        message: err instanceof Error ? err.message : "Failed to save marks.",
        type: "error",
      });
    },
  });

  // Lock / Unlock Mutations
  const lockMutation = useMutation({
    mutationFn: () => examsApi.lockMarks(selectedSubject),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exam-subjects"] });
      setNotification({ message: "Marks locked successfully.", type: "success" });
    },
  });

  const unlockMutation = useMutation({
    mutationFn: () => examsApi.unlockMarks(selectedSubject, "Administrative adjustment requested"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exam-subjects"] });
      setNotification({ message: "Marks unlocked successfully.", type: "success" });
    },
  });

  const fullMarks = currentSubject ? parseFloat(currentSubject.full_marks || "100") : 100;
  const cqMax = currentSubject ? parseFloat(currentSubject.creative_full_marks || "70") : 70;
  const cqPass = currentSubject ? parseFloat(currentSubject.creative_pass_marks || "23") : 23;
  const mcqMax = currentSubject ? parseFloat(currentSubject.mcq_full_marks || "30") : 30;
  const mcqPass = currentSubject ? parseFloat(currentSubject.mcq_pass_marks || "10") : 10;
  const prMax = currentSubject ? parseFloat(currentSubject.practical_full_marks || "0") : 0;
  const isLocked = Boolean(currentSubject?.is_marks_locked);

  // Filtered rows by search
  const filteredRows = useMemo(() => {
    const list = Object.values(marksState);
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter((r) => r.name.toLowerCase().includes(q) || r.code.toLowerCase().includes(q));
  }, [marksState, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/exams" className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("exams.markEntryTitle", "Examinations Mark Entry Sheet")}
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t(
              "exams.markEntrySubtitle",
              "Enter and evaluate continuous assessment marks (CQ, MCQ, Practical) with live GPA 5.0 grade verification."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedSubject && (
            <>
              {isLocked ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => unlockMutation.mutate()}
                  className="h-9 gap-1.5 text-xs text-amber-700 border-amber-300"
                >
                  <Unlock className="h-3.5 w-3.5" />
                  Unlock Marks
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => lockMutation.mutate()}
                  className="h-9 gap-1.5 text-xs text-slate-700"
                >
                  <Lock className="h-3.5 w-3.5" />
                  Lock Final Marks
                </Button>
              )}
              <Button
                size="sm"
                disabled={isLocked || saveMarksMutation.isPending}
                onClick={() => saveMarksMutation.mutate()}
                className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
              >
                <Save className="h-3.5 w-3.5" />
                {saveMarksMutation.isPending ? t("common.saving", "Saving...") : t("common.save", "Save Marks")}
              </Button>
            </>
          )}
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

      {/* Selector Ribbon */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label htmlFor="mark-entry-exam" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Exam Cycle *</label>
            <select
              id="mark-entry-exam"
              value={selectedExam}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedExam(val);
                setSelectedSubject("");
                updateParams({ exam: val, subject: "" });
              }}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">Select Examination...</option>
              {exams.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="mark-entry-class" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Class Grade *</label>
            <select
              id="mark-entry-class"
              value={selectedClass}
              disabled={!selectedExam}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedClass(val);
                setSelectedSection("");
                setSelectedSubject("");
                updateParams({ class: val, section: "", subject: "" });
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
            <label htmlFor="mark-entry-section" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Section *</label>
            <select
              id="mark-entry-section"
              value={selectedSection}
              disabled={!selectedClass}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedSection(val);
                updateParams({ section: val });
              }}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50"
            >
              <option value="">Select Section...</option>
              {sectionsData.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="mark-entry-subject" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Exam Subject *</label>
            <select
              id="mark-entry-subject"
              value={selectedSubject}
              disabled={!selectedClass || examSubjects.length === 0}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedSubject(val);
                updateParams({ subject: val });
              }}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50"
            >
              <option value="">Select Exam Subject...</option>
              {examSubjects.map((sub) => (
                <option key={sub.id} value={sub.id}>
                  {sub.subject_name_en} ({sub.subject_code})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Component Caps info bar */}
        {currentSubject && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                {currentSubject.subject_name_en}
              </span>
              <span className="text-slate-500">
                Full: <span className="font-mono font-semibold">{fullMarks}</span>
              </span>
              {cqMax > 0 && (
                <span className="text-slate-500">
                  CQ: <span className="font-mono font-semibold">{cqMax}</span> (Pass: {cqPass})
                </span>
              )}
              {mcqMax > 0 && (
                <span className="text-slate-500">
                  MCQ: <span className="font-mono font-semibold">{mcqMax}</span> (Pass: {mcqPass})
                </span>
              )}
              {prMax > 0 && (
                <span className="text-slate-500">
                  Practical: <span className="font-mono font-semibold">{prMax}</span>
                </span>
              )}
            </div>

            {isLocked && (
              <span className="inline-flex items-center gap-1 font-semibold text-rose-600 dark:text-rose-400">
                <Lock className="h-3.5 w-3.5" /> Marks are officially locked
              </span>
            )}
          </div>
        )}
      </div>

      {/* Spreadsheet Table */}
      {!selectedSection || !selectedSubject ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          <FileCheck2 className="mx-auto mb-2 h-8 w-8 text-slate-300" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">Select Exam, Class, Section, and Subject above</p>
          <p className="mt-1 text-slate-400">The spreadsheet mark entry roster will populate automatically.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="relative w-72">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search candidate name or roll..."
                className="h-8 pl-8 text-xs"
              />
            </div>
            <div className="text-xs text-slate-500">
              Total Enrolled Candidates: <span className="font-semibold text-slate-900 dark:text-slate-100">{filteredRows.length}</span>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {isStudentsLoading ? (
              <div className="p-8 text-center text-xs text-slate-500">Loading student roster...</div>
            ) : filteredRows.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">No students found matching this criteria.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-2.5 font-semibold w-12 text-center">Roll</th>
                      <th className="px-4 py-2.5 font-semibold">Candidate Student</th>
                      {cqMax > 0 && <th className="px-3 py-2.5 font-semibold w-24">CQ (Max {cqMax})</th>}
                      {mcqMax > 0 && <th className="px-3 py-2.5 font-semibold w-24">MCQ (Max {mcqMax})</th>}
                      {prMax > 0 && <th className="px-3 py-2.5 font-semibold w-24">PR (Max {prMax})</th>}
                      <th className="px-3 py-2.5 font-semibold w-16 text-center">Absent</th>
                      <th className="px-3 py-2.5 font-semibold w-20 text-center">Total</th>
                      <th className="px-3 py-2.5 font-semibold w-16 text-center">Grade</th>
                      <th className="px-3 py-2.5 font-semibold w-16 text-center">GP</th>
                      <th className="px-3 py-2.5 font-semibold text-right">Evaluation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {filteredRows.map((row) => {
                      const cqVal = parseFloat(row.cq) || 0;
                      const mcqVal = parseFloat(row.mcq) || 0;
                      const prVal = parseFloat(row.practical) || 0;
                      const totalMarks = cqVal + mcqVal + prVal;

                      const evaluation = calculateBdGrade(
                        totalMarks,
                        fullMarks,
                        cqVal,
                        cqPass,
                        mcqVal,
                        mcqPass,
                        row.is_absent
                      );

                      return (
                        <tr
                          key={row.student_id}
                          className={`hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors ${
                            row.is_absent ? "bg-slate-50/80 dark:bg-slate-900/40 opacity-75" : ""
                          }`}
                        >
                          <td className="px-3 py-2 text-center font-mono font-semibold text-slate-700 dark:text-slate-300">
                            {row.roll_no}
                          </td>
                          <td className="px-4 py-2">
                            <div className="font-medium text-slate-900 dark:text-slate-100">{row.name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{row.code}</div>
                          </td>

                          {/* CQ Input */}
                          {cqMax > 0 && (
                            <td className="px-3 py-2">
                              <Input
                                type="number"
                                disabled={isLocked || row.is_absent}
                                value={row.cq}
                                max={cqMax}
                                min={0}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setMarksState((prev) => ({
                                    ...prev,
                                    [row.student_id]: { ...prev[row.student_id]!, cq: val },
                                  }));
                                }}
                                className={`h-8 w-20 text-xs font-mono ${
                                  cqVal > cqMax ? "border-rose-500 bg-rose-50 dark:bg-rose-950" : ""
                                }`}
                              />
                            </td>
                          )}

                          {/* MCQ Input */}
                          {mcqMax > 0 && (
                            <td className="px-3 py-2">
                              <Input
                                type="number"
                                disabled={isLocked || row.is_absent}
                                value={row.mcq}
                                max={mcqMax}
                                min={0}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setMarksState((prev) => ({
                                    ...prev,
                                    [row.student_id]: { ...prev[row.student_id]!, mcq: val },
                                  }));
                                }}
                                className={`h-8 w-20 text-xs font-mono ${
                                  mcqVal > mcqMax ? "border-rose-500 bg-rose-50 dark:bg-rose-950" : ""
                                }`}
                              />
                            </td>
                          )}

                          {/* Practical Input */}
                          {prMax > 0 && (
                            <td className="px-3 py-2">
                              <Input
                                type="number"
                                disabled={isLocked || row.is_absent}
                                value={row.practical}
                                max={prMax}
                                min={0}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setMarksState((prev) => ({
                                    ...prev,
                                    [row.student_id]: { ...prev[row.student_id]!, practical: val },
                                  }));
                                }}
                                className="h-8 w-20 text-xs font-mono"
                              />
                            </td>
                          )}

                          {/* Absent Checkbox */}
                          <td className="px-3 py-2 text-center">
                            <input
                              type="checkbox"
                              disabled={isLocked}
                              checked={row.is_absent}
                              onChange={(e) => {
                                const checked = e.target.checked;
                                setMarksState((prev) => ({
                                  ...prev,
                                  [row.student_id]: {
                                    ...prev[row.student_id]!,
                                    is_absent: checked,
                                    cq: checked ? "" : prev[row.student_id]!.cq,
                                    mcq: checked ? "" : prev[row.student_id]!.mcq,
                                    practical: checked ? "" : prev[row.student_id]!.practical,
                                  },
                                }));
                              }}
                              className="h-4 w-4 rounded-sm border-slate-300 text-emerald-800"
                            />
                          </td>

                          {/* Total */}
                          <td className="px-3 py-2 text-center font-mono font-bold text-slate-900 dark:text-slate-100">
                            {row.is_absent ? "-" : totalMarks.toFixed(1)}
                          </td>

                          {/* Grade */}
                          <td className="px-3 py-2 text-center">
                            <span
                              className={`inline-block rounded-sm px-1.5 py-0.5 text-[10px] font-bold ${
                                evaluation.grade === "A+"
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                  : evaluation.grade === "F" || evaluation.grade === "ABS"
                                  ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                                  : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                              }`}
                            >
                              {evaluation.grade}
                            </span>
                          </td>

                          {/* GP */}
                          <td className="px-3 py-2 text-center font-mono font-semibold text-slate-700 dark:text-slate-300">
                            {evaluation.gp.toFixed(2)}
                          </td>

                          {/* Reason */}
                          <td className="px-3 py-2 text-right">
                            {!evaluation.isPassed ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-600">
                                <ShieldAlert className="h-3 w-3" /> {evaluation.reason}
                              </span>
                            ) : (
                              <span className="text-[10px] text-emerald-700 font-semibold">Pass</span>
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
        </div>
      )}
    </div>
  );
}
