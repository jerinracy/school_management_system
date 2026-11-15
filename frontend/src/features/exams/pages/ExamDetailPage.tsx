import { useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  BookOpen,
  Calendar,
  CheckCircle2,
  FileCheck2,
  FileText,
  Lock,
  Plus,
  Printer,
  ShieldCheck,
  Unlock,
  UserCheck,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { examsApi } from "@/features/exams/api/examsApi";
import { examSubjectFormSchema, type ExamSubjectFormData } from "@/features/exams/schemas/examSchemas";
import { academicApi } from "@/features/academics/api/academicApi";

export default function ExamDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"subjects" | "eligibility" | "admit_cards" | "routines">("subjects");
  const [showAddSubjectModal, setShowAddSubjectModal] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Queries
  const { data: exam, isLoading: isExamLoading } = useQuery({
    queryKey: ["exam-detail", id],
    queryFn: () => examsApi.getExam(id!),
    enabled: Boolean(id),
  });

  const { data: examSubjectsData, isLoading: isSubjectsLoading } = useQuery({
    queryKey: ["exam-subjects", id],
    queryFn: () => examsApi.getExamSubjects({ exam: id }),
    enabled: Boolean(id),
  });

  const { data: eligibilitiesData } = useQuery({
    queryKey: ["exam-eligibilities", id],
    queryFn: () => examsApi.getEligibilities({ exam: id }),
    enabled: Boolean(id) && activeTab === "eligibility",
  });

  const { data: admitCardsData } = useQuery({
    queryKey: ["exam-admit-cards", id],
    queryFn: () => examsApi.getAdmitCards({ exam: id }),
    enabled: Boolean(id) && activeTab === "admit_cards",
  });

  const { data: routinesData } = useQuery({
    queryKey: ["exam-routines", id],
    queryFn: () => examsApi.getRoutines({ exam: id }),
    enabled: Boolean(id) && activeTab === "routines",
  });

  const { data: classesData = [] } = useQuery({
    queryKey: ["academic-classes"],
    queryFn: () => academicApi.getClasses(),
  });

  const { data: subjectsData = [] } = useQuery({
    queryKey: ["academic-subjects"],
    queryFn: () => academicApi.getSubjects(),
  });

  const examSubjects = useMemo(() => examSubjectsData?.results ?? [], [examSubjectsData]);
  const eligibilities = useMemo(() => eligibilitiesData?.results ?? [], [eligibilitiesData]);
  const admitCards = useMemo(() => admitCardsData?.results ?? [], [admitCardsData]);
  const routines = useMemo(() => routinesData?.results ?? [], [routinesData]);

  // Form for New Exam Subject
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExamSubjectFormData>({
    resolver: zodResolver(examSubjectFormSchema),
    defaultValues: {
      subject: "",
      class_level: "",
      full_marks: "100.00",
      pass_marks: "33.00",
      creative_full_marks: "70.00",
      creative_pass_marks: "23.00",
      mcq_full_marks: "30.00",
      mcq_pass_marks: "10.00",
      practical_full_marks: "0.00",
      practical_pass_marks: "0.00",
    },
  });

  // Mutations
  const addSubjectMutation = useMutation({
    mutationFn: (data: ExamSubjectFormData) =>
      examsApi.createExamSubject({
        exam: id!,
        class_level: data.class_level,
        subject: data.subject,
        exam_date: data.exam_date || null,
        start_time: data.start_time || null,
        end_time: data.end_time || null,
        full_marks: data.full_marks,
        pass_marks: data.pass_marks,
        creative_full_marks: data.creative_full_marks,
        creative_pass_marks: data.creative_pass_marks,
        mcq_full_marks: data.mcq_full_marks,
        mcq_pass_marks: data.mcq_pass_marks,
        practical_full_marks: data.practical_full_marks,
        practical_pass_marks: data.practical_pass_marks,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exam-subjects", id] });
      setShowAddSubjectModal(false);
      reset();
      setNotification({ message: "Exam subject successfully added.", type: "success" });
    },
    onError: (err: unknown) => {
      setNotification({
        message: err instanceof Error ? err.message : "Failed to add exam subject.",
        type: "error",
      });
    },
  });

  const generateEligibilityMutation = useMutation({
    mutationFn: () => examsApi.generateEligibility(id!),
    onSuccess: (data: unknown) => {
      void queryClient.invalidateQueries({ queryKey: ["exam-eligibilities", id] });
      setNotification({
        message: (data as { message?: string })?.message || "Candidate eligibility evaluated successfully.",
        type: "success",
      });
    },
  });

  const generateAdmitCardsMutation = useMutation({
    mutationFn: () => examsApi.generateAdmitCards(id!),
    onSuccess: (data: unknown) => {
      void queryClient.invalidateQueries({ queryKey: ["exam-admit-cards", id] });
      setNotification({
        message: (data as { message?: string })?.message || "Admit cards generated successfully.",
        type: "success",
      });
    },
  });

  if (isExamLoading) {
    return <div className="p-12 text-center text-xs text-slate-500">Loading examination details...</div>;
  }

  if (!exam) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center text-xs text-rose-700">
        Examination record not found.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button & Title */}
      <div>
        <Link to="/exams" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 mb-2">
          <ArrowLeft className="h-3.5 w-3.5" />
          {t("common.backToExams", "Back to Examinations")}
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{exam.name}</h1>
              <span
                className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                  exam.status === "published"
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    : exam.status === "locked"
                    ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                    : exam.status === "in_progress" || exam.status === "marking"
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                    : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {exam.status}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Session: <span className="font-semibold text-slate-700 dark:text-slate-300">{exam.session_name}</span> | Type:{" "}
              <span className="font-semibold text-slate-700 dark:text-slate-300">{exam.exam_type_name}</span> | Window:{" "}
              <span className="font-mono text-slate-700 dark:text-slate-300">{exam.start_date} to {exam.end_date}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/exams/marks?exam=${exam.id}`}>
              <Button size="sm" className="h-9 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs">
                <FileCheck2 className="h-3.5 w-3.5" />
                {t("exams.markEntryPortal", "Mark Entry Sheet")}
              </Button>
            </Link>
            <Link to={`/results?exam=${exam.id}`}>
              <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs border-emerald-300 text-emerald-800 dark:border-emerald-800 dark:text-emerald-300">
                <Award className="h-3.5 w-3.5" />
                {t("results.processResults", "Process Results")}
              </Button>
            </Link>
          </div>
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

      {/* Tabs Navigation */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab("subjects")}
          className={`flex items-center gap-1.5 pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "subjects"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-400 dark:text-emerald-300"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <BookOpen className="h-3.5 w-3.5" />
          Subjects & Marks ({examSubjects.length})
        </button>
        <button
          onClick={() => setActiveTab("eligibility")}
          className={`flex items-center gap-1.5 pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "eligibility"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-400 dark:text-emerald-300"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <UserCheck className="h-3.5 w-3.5" />
          Candidate Eligibility
        </button>
        <button
          onClick={() => setActiveTab("admit_cards")}
          className={`flex items-center gap-1.5 pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "admit_cards"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-400 dark:text-emerald-300"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <FileText className="h-3.5 w-3.5" />
          Admit Cards
        </button>
        <button
          onClick={() => setActiveTab("routines")}
          className={`flex items-center gap-1.5 pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "routines"
              ? "border-emerald-700 text-emerald-800 dark:border-emerald-400 dark:text-emerald-300"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Calendar className="h-3.5 w-3.5" />
          Exam Routine
        </button>
      </div>

      {/* TAB 1: Subjects & Marks */}
      {activeTab === "subjects" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              Configured curriculum subjects, component mark distributions (CQ, MCQ, Practical), and pass criteria for this exam.
            </p>
            <Button
              size="sm"
              onClick={() => setShowAddSubjectModal(true)}
              className="h-8 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Exam Subject
            </Button>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {isSubjectsLoading ? (
              <div className="p-8 text-center text-xs text-slate-500">Loading subjects...</div>
            ) : examSubjects.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No subjects configured for this examination yet. Click &quot;Add Exam Subject&quot; above.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Subject & Code</th>
                      <th className="px-4 py-3 font-semibold">Class Grade</th>
                      <th className="px-4 py-3 font-semibold">Full Marks</th>
                      <th className="px-4 py-3 font-semibold">CQ (Theory)</th>
                      <th className="px-4 py-3 font-semibold">MCQ</th>
                      <th className="px-4 py-3 font-semibold">Practical</th>
                      <th className="px-4 py-3 font-semibold">Lock Status</th>
                      <th className="px-4 py-3 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {examSubjects.map((sub) => (
                      <tr key={sub.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                          <div>{sub.subject_name_en}</div>
                          <div className="text-[11px] text-slate-400 font-mono">{sub.subject_code}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{sub.class_level_name}</td>
                        <td className="px-4 py-3 font-mono font-semibold text-slate-900 dark:text-slate-100">
                          {sub.full_marks || "100.00"}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                          {sub.creative_full_marks || "0"}{" "}
                          <span className="text-[10px] text-slate-400">(Pass: {sub.creative_pass_marks || "0"})</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                          {sub.mcq_full_marks || "0"}{" "}
                          <span className="text-[10px] text-slate-400">(Pass: {sub.mcq_pass_marks || "0"})</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                          {sub.practical_full_marks || "0"}
                        </td>
                        <td className="px-4 py-3">
                          {sub.is_marks_locked ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 dark:text-rose-400">
                              <Lock className="h-3 w-3" /> Locked
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                              <Unlock className="h-3 w-3" /> Open
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link to={`/exams/marks?exam=${exam.id}&subject=${sub.id}`}>
                            <Button variant="outline" size="sm" className="h-7 px-2.5 text-xs">
                              Enter Marks
                            </Button>
                          </Link>
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

      {/* TAB 2: Candidate Eligibility */}
      {activeTab === "eligibility" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              Evaluates enrolled students against attendance threshold (minimum 75%) and fee dues clearance.
            </p>
            <Button
              size="sm"
              disabled={generateEligibilityMutation.isPending}
              onClick={() => generateEligibilityMutation.mutate()}
              className="h-8 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              {generateEligibilityMutation.isPending ? "Evaluating..." : "Run Eligibility Evaluation"}
            </Button>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {eligibilities.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No eligibility records evaluated yet. Click &quot;Run Eligibility Evaluation&quot;.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Candidate Student</th>
                      <th className="px-4 py-3 font-semibold">Attendance %</th>
                      <th className="px-4 py-3 font-semibold">Attendance Rule</th>
                      <th className="px-4 py-3 font-semibold">Fee Clearance</th>
                      <th className="px-4 py-3 font-semibold">Final Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {eligibilities.map((el) => {
                      const isAttEligible = parseFloat(el.attendance_percentage || "0") >= 75;
                      const isFeeCleared = Boolean(el.dues_cleared);
                      const isEligible = el.clearance_status === "eligible" || el.clearance_status === "cleared_by_principal";
                      return (
                        <tr key={el.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                            {el.student_name_en || el.student_name_bn}
                          </td>
                          <td className="px-4 py-3 font-mono font-semibold">
                            {el.attendance_percentage || "0.00"}%
                          </td>
                          <td className="px-4 py-3">
                            {isAttEligible ? (
                              <span className="text-emerald-700 font-semibold text-[11px]">Eligible (&ge;75%)</span>
                            ) : (
                              <span className="text-rose-600 font-semibold text-[11px]">Short Attendance</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {isFeeCleared ? (
                              <span className="text-emerald-700 font-semibold text-[11px]">Cleared</span>
                            ) : (
                              <span className="text-amber-600 font-semibold text-[11px]">Has Dues</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                                isEligible
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                  : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                              }`}
                            >
                              {isEligible ? "Admit Allowed" : "Barred / Ineligible"}
                            </span>
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

      {/* TAB 3: Admit Cards */}
      {activeTab === "admit_cards" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              Official examination hall passes with student registration, photo frame, and schedule table.
            </p>
            <div className="flex items-center gap-2">
              <Link to={`/exams/admit-cards?exam=${exam.id}`}>
                <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                  <Printer className="h-3.5 w-3.5" />
                  Printable Center
                </Button>
              </Link>
              <Button
                size="sm"
                disabled={generateAdmitCardsMutation.isPending}
                onClick={() => generateAdmitCardsMutation.mutate()}
                className="h-8 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
              >
                <FileText className="h-3.5 w-3.5" />
                {generateAdmitCardsMutation.isPending ? "Generating..." : "Generate Admit Cards"}
              </Button>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {admitCards.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No admit cards issued yet. Click &quot;Generate Admit Cards&quot;.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Candidate</th>
                      <th className="px-4 py-3 font-semibold">Roll & Section</th>
                      <th className="px-4 py-3 font-semibold">Admit Card Number</th>
                      <th className="px-4 py-3 font-semibold">Issue Date</th>
                      <th className="px-4 py-3 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {admitCards.map((ac) => (
                      <tr key={ac.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                          {ac.student_name_en || ac.student_name_bn}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-400">
                          ID: {ac.student_id}
                        </td>
                        <td className="px-4 py-3 font-mono font-semibold text-emerald-800 dark:text-emerald-400">
                          {ac.card_number}
                        </td>
                        <td className="px-4 py-3 text-slate-500">
                          {ac.issue_date || "Generated"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button variant="ghost" size="sm" className="h-7 px-2.5 text-xs text-emerald-800 dark:text-emerald-400">
                            View Pass
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

      {/* TAB 4: Exam Routine */}
      {activeTab === "routines" && (
        <div className="space-y-4">
          <p className="text-xs text-slate-500">
            Timetable schedule of examination papers, hall/room allocations, and shifts.
          </p>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
            {routines.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No examination routines scheduled yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Exam Date</th>
                      <th className="px-4 py-3 font-semibold">Subject</th>
                      <th className="px-4 py-3 font-semibold">Time Window</th>
                      <th className="px-4 py-3 font-semibold">Room / Hall</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {routines.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3 font-mono font-semibold">{r.exam_date}</td>
                        <td className="px-4 py-3">{r.subject_name_en}</td>
                        <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                          {r.start_time?.slice(0, 5)} - {r.end_time?.slice(0, 5)}
                        </td>
                        <td className="px-4 py-3">{r.room_number || "Main Hall"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Add Exam Subject */}
      {showAddSubjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Add Subject to Examination
              </h2>
              <button
                onClick={() => setShowAddSubjectModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                void handleSubmit((data) => addSubjectMutation.mutate(data))(e);
              }}
              className="space-y-3.5 text-xs"
            >
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="subject-class-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Class Grade *</label>
                  <select
                    id="subject-class-select"
                    {...register("class_level")}
                    className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="">Select Class...</option>
                    {classesData.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  {errors.class_level && <p className="mt-1 text-[11px] text-rose-600">{errors.class_level.message}</p>}
                </div>

                <div>
                  <label htmlFor="subject-item-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Curriculum Subject *</label>
                  <select
                    id="subject-item-select"
                    {...register("subject")}
                    className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="">Select Subject...</option>
                    {subjectsData.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name_en || s.name_bn} ({s.code})
                      </option>
                    ))}
                  </select>
                  {errors.subject && <p className="mt-1 text-[11px] text-rose-600">{errors.subject.message}</p>}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="full-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Total Full Marks *</label>
                  <Input id="full-marks-input" {...register("full_marks")} className="h-9 text-xs font-mono" />
                </div>
                <div>
                  <label htmlFor="pass-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Total Pass Marks *</label>
                  <Input id="pass-marks-input" {...register("pass_marks")} className="h-9 text-xs font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="cq-full-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">CQ (Theory) Max</label>
                  <Input id="cq-full-marks-input" {...register("creative_full_marks")} className="h-9 text-xs font-mono" />
                </div>
                <div>
                  <label htmlFor="cq-pass-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">CQ Pass Mark</label>
                  <Input id="cq-pass-marks-input" {...register("creative_pass_marks")} className="h-9 text-xs font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="mcq-full-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">MCQ Max</label>
                  <Input id="mcq-full-marks-input" {...register("mcq_full_marks")} className="h-9 text-xs font-mono" />
                </div>
                <div>
                  <label htmlFor="mcq-pass-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">MCQ Pass Mark</label>
                  <Input id="mcq-pass-marks-input" {...register("mcq_pass_marks")} className="h-9 text-xs font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="pr-full-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Practical Max</label>
                  <Input id="pr-full-marks-input" {...register("practical_full_marks")} className="h-9 text-xs font-mono" />
                </div>
                <div>
                  <label htmlFor="pr-pass-marks-input" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Practical Pass Mark</label>
                  <Input id="pr-pass-marks-input" {...register("practical_pass_marks")} className="h-9 text-xs font-mono" />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <Button type="button" variant="outline" size="sm" onClick={() => setShowAddSubjectModal(false)}>
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={addSubjectMutation.isPending}
                  className="bg-emerald-800 hover:bg-emerald-900 text-white"
                >
                  {addSubjectMutation.isPending ? t("common.saving", "Saving...") : "Add Subject"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
