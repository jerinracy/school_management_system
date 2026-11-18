import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  FileCheck2,
  FileText,
  Plus,
  Search,
  Tag,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { examsApi } from "@/features/exams/api/examsApi";
import { examFormSchema, type ExamFormData } from "@/features/exams/schemas/examSchemas";
import { institutionApi } from "@/features/institutions/api/institutionApi";

export default function ExamListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedSession, setSelectedSession] = useState<string>("ALL");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Exam Types Management State
  const [showExamTypesModal, setShowExamTypesModal] = useState(false);
  const [showCreateTypeModal, setShowCreateTypeModal] = useState(false);
  const [newTypeName, setNewTypeName] = useState("");
  const [newTypeCode, setNewTypeCode] = useState("");
  const [newTypeIsBoard, setNewTypeIsBoard] = useState(false);
  const [newTypeDescription, setNewTypeDescription] = useState("");
  const [typeActionError, setTypeActionError] = useState<string | null>(null);
  const [deletingTypeId, setDeletingTypeId] = useState<string | null>(null);

  // Queries
  const { data: examsData, isLoading } = useQuery({
    queryKey: ["exams-list", selectedSession, statusFilter, search],
    queryFn: () =>
      examsApi.getExams({
        session: selectedSession !== "ALL" ? selectedSession : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        search: search.trim() || undefined,
      }),
  });

  const { data: examTypes = [] } = useQuery({
    queryKey: ["exam-types"],
    queryFn: () => examsApi.getExamTypes(),
  });

  const { data: sessionsData = [] } = useQuery({
    queryKey: ["academic-sessions"],
    queryFn: () => institutionApi.getSessions(),
  });

  const exams = useMemo(() => examsData?.results ?? [], [examsData]);
  const sessions = useMemo(() => sessionsData, [sessionsData]);

  // Form for New Exam
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<ExamFormData>({
    resolver: zodResolver(examFormSchema),
    defaultValues: {
      name: "",
      exam_type: "",
      session: "",
      start_date: new Date().toISOString().split("T")[0],
      end_date: new Date().toISOString().split("T")[0],
      term: "Term 1",
      weightage: "100.00",
    },
  });

  // Create Mutation
  const createExamMutation = useMutation({
    mutationFn: (data: ExamFormData) => examsApi.createExam(data),
    onSuccess: (newExam) => {
      void queryClient.invalidateQueries({ queryKey: ["exams-list"] });
      setShowCreateModal(false);
      reset();
      void navigate(`/exams/${newExam.id}`);
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : "Failed to create examination term.");
    },
  });

  // Create Exam Type Mutation
  const createExamTypeMutation = useMutation({
    mutationFn: (data: {
      name: string;
      code: string;
      is_board_exam?: boolean;
      description?: string;
    }) => examsApi.createExamType(data),
    onSuccess: (newType) => {
      void queryClient.invalidateQueries({ queryKey: ["exam-types"] });
      setShowCreateTypeModal(false);
      setNewTypeName("");
      setNewTypeCode("");
      setNewTypeIsBoard(false);
      setNewTypeDescription("");
      setTypeActionError(null);
      setValue("exam_type", newType.id);
    },
    onError: (err: unknown) => {
      setTypeActionError(err instanceof Error ? err.message : "Failed to create exam type.");
    },
  });

  // Delete Exam Type Mutation
  const deleteExamTypeMutation = useMutation({
    mutationFn: (id: string) => examsApi.deleteExamType(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["exam-types"] });
      setDeletingTypeId(null);
    },
    onError: (err: unknown) => {
      setTypeActionError(
        err instanceof Error
          ? err.message
          : "Failed to delete exam type. It may be linked to existing examinations.",
      );
    },
  });

  // KPI Overview
  const kpis = useMemo(() => {
    const total = exams.length;
    const ongoing = exams.filter((e) => e.status === "in_progress" || e.status === "marking").length;
    const concluded = exams.filter((e) => e.status === "locked").length;
    const published = exams.filter((e) => e.status === "published").length;
    return { total, ongoing, concluded, published };
  }, [exams]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          {t("exams.title", "Examinations & Continuous Assessment")}
        </h1>

        <div className="flex flex-wrap items-center gap-2">
          <Link to="/exams/marks">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100">
              <FileCheck2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              {t("exams.markEntryPortal", "Mark Entry Sheet")}
            </Button>
          </Link>
          <Link to="/results">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100">
              <BookOpen className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
              {t("results.resultsHub", "GPA 5.0 Processing")}
            </Button>
          </Link>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setTypeActionError(null);
              setShowExamTypesModal(true);
            }}
            className="h-9 gap-1.5 text-xs text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
          >
            <Tag className="h-3.5 w-3.5 text-slate-500" />
            {t("exams.manageExamTypes", "Exam Types")}
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setActionError(null);
              setShowCreateModal(true);
            }}
            className="h-9 gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold shadow-xs dark:bg-emerald-600 dark:hover:bg-emerald-500"
          >
            <Plus className="h-3.5 w-3.5" />
            {t("exams.newExam", "Create Examination")}
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Exams</span>
            <BookOpen className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">{kpis.total}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Active / Ongoing</span>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-600 dark:text-amber-400">{kpis.ongoing}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Concluded / Tabulated</span>
            <FileText className="h-4 w-4 text-blue-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-blue-600 dark:text-blue-400">{kpis.concluded}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Formally Published</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-700 dark:text-emerald-300">{kpis.published}</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("exams.searchPlaceholder", "Search examinations...")}
            className="h-9 pl-9 text-xs"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <select
            value={selectedSession}
            onChange={(e) => setSelectedSession(e.target.value)}
            className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="ALL">All Academic Sessions</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="ALL">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="scheduled">Scheduled</option>
            <option value="ongoing">Ongoing</option>
            <option value="concluded">Concluded</option>
            <option value="tabulated">Tabulated</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      {/* Exams Roster Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading examinations...</div>
        ) : exams.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <BookOpen className="mx-auto mb-2 h-8 w-8 text-slate-300" />
            <p className="font-semibold text-slate-700 dark:text-slate-300">No examinations found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-semibold">Exam Title & Term</th>
                  <th className="px-4 py-3 font-semibold">Session & Type</th>
                  <th className="px-4 py-3 font-semibold">Date Window</th>
                  <th className="px-4 py-3 font-semibold">Subjects</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {exams.map((exam) => (
                  <tr key={exam.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{exam.name}</div>
                      <div className="text-[11px] text-slate-400">{exam.term || "Regular Term"}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-slate-700 dark:text-slate-300">{exam.session_name}</div>
                      <div className="text-[11px] text-slate-400">{exam.exam_type_name}</div>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-slate-400" />
                        <span>{exam.start_date} to {exam.end_date}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        <BookOpen className="h-3 w-3 text-slate-400" />
                        {exam.exam_subjects_count} subjects
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
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
                    </td>
                    <td className="px-4 py-3.5 text-right space-x-1">
                      <Link to={`/exams/${exam.id}`}>
                        <Button variant="ghost" size="sm" className="h-7 px-2.5 text-xs text-emerald-800 hover:text-emerald-900 dark:text-emerald-400">
                          Workspace
                        </Button>
                      </Link>
                      <Link to={`/exams/marks?exam=${exam.id}`}>
                        <Button variant="outline" size="sm" className="h-7 px-2.5 text-xs">
                          Marks
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

      {/* Modal: Create Examination */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="sm:max-w-lg p-6">
          <DialogHeader className="pr-6">
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Plus className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
              {t("exams.createExamModalTitle", "Create Examination Cycle")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500 dark:text-slate-400">
              {t(
                "exams.createExamModalSubtitle",
                "Define a new examination term, associate an academic session and configure grading weightage."
              )}
            </DialogDescription>
          </DialogHeader>

          {actionError && (
            <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          <form
            onSubmit={(e) => {
              void handleSubmit((data) => createExamMutation.mutate(data))(e);
            }}
            className="space-y-3.5 text-xs mt-2"
          >
            <div>
              <label htmlFor="exam-name" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                Exam Title *
              </label>
              <Input
                id="exam-name"
                {...register("name")}
                placeholder="e.g. Annual Examination 2026 / বার্ষিক পরীক্ষা ২০২৬"
                className="h-9 text-xs"
              />
              {errors.name && <p className="mt-1 text-[11px] text-rose-600">{errors.name.message}</p>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label htmlFor="exam-type-select" className="block text-slate-600 dark:text-slate-400 font-medium">
                    {t("exams.examType", "Exam Type")} *
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setTypeActionError(null);
                      setShowCreateTypeModal(true);
                    }}
                    className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 dark:text-emerald-400 hover:underline flex items-center gap-0.5 cursor-pointer"
                  >
                    <Plus className="h-3 w-3" />
                    <span>{t("exams.newType", "New Type")}</span>
                  </button>
                </div>
                <select
                  id="exam-type-select"
                  {...register("exam_type")}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
                >
                  <option value="">{t("exams.selectType", "Select Type...")}</option>
                  {examTypes.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.code})
                    </option>
                  ))}
                </select>
                {errors.exam_type && <p className="mt-1 text-[11px] text-rose-600">{errors.exam_type.message}</p>}
              </div>

              <div>
                <label htmlFor="exam-session-select" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  Academic Session *
                </label>
                <select
                  id="exam-session-select"
                  {...register("session")}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
                >
                  <option value="">Select Session...</option>
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                {errors.session && <p className="mt-1 text-[11px] text-rose-600">{errors.session.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="exam-start-date" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  Start Date *
                </label>
                <Input id="exam-start-date" type="date" {...register("start_date")} className="h-9 text-xs font-mono" />
              </div>
              <div>
                <label htmlFor="exam-end-date" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  End Date *
                </label>
                <Input id="exam-end-date" type="date" {...register("end_date")} className="h-9 text-xs font-mono" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="exam-term" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  Term Name
                </label>
                <Input id="exam-term" {...register("term")} placeholder="e.g. 1st Terminal / Final" className="h-9 text-xs" />
              </div>
              <div>
                <label htmlFor="exam-weightage" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  Annual Weightage (%)
                </label>
                <Input id="exam-weightage" {...register("weightage")} placeholder="100.00" className="h-9 text-xs font-mono" />
              </div>
            </div>

            <DialogFooter className="pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={createExamMutation.isPending}
                className="bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {createExamMutation.isPending ? t("common.saving", "Saving...") : t("exams.createButton", "Create & Configure")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Manage Exam Types Modal */}
      <Dialog open={showExamTypesModal} onOpenChange={setShowExamTypesModal}>
        <DialogContent className="sm:max-w-xl max-h-[85vh] flex flex-col p-6">
          <DialogHeader className="pr-6">
            <div>
              <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Tag className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
                {t("exams.examTypesModalTitle", "Manage Examination Types")}
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {t(
                  "exams.examTypesModalSubtitle",
                  "Configure institution-specific examination cycles, term classifications, and board exam indicators."
                )}
              </DialogDescription>
            </div>
          </DialogHeader>

          {typeActionError && (
            <div className="rounded-md bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
              <span>{typeActionError}</span>
            </div>
          )}

          <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {examTypes.length} {t("exams.manageExamTypes", "Exam Types")}
            </span>
            <Button
              size="sm"
              onClick={() => {
                setTypeActionError(null);
                setShowCreateTypeModal(true);
              }}
              className="h-8 gap-1.5 bg-emerald-800 text-white hover:bg-emerald-900 text-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              {t("exams.addExamType", "Add Examination Type")}
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 max-h-[50vh] pr-1">
            {examTypes.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                {t("exams.noExamTypes", "No examination types configured yet.")}
              </div>
            ) : (
              examTypes.map((type) => (
                <div key={type.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">{type.name}</span>
                      <span className="font-mono text-[10px] bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-600 dark:text-slate-400">
                        {type.code}
                      </span>
                      {type.is_board_exam && (
                        <Badge variant="amber" className="text-[10px]">
                          {t("exams.typeIsBoard", "Board Exam")}
                        </Badge>
                      )}
                    </div>
                    {type.description && (
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-sm">
                        {type.description}
                      </p>
                    )}
                  </div>

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={deleteExamTypeMutation.isPending && deletingTypeId === type.id}
                    onClick={() => {
                      if (window.confirm(t("exams.deleteTypeConfirm", "Are you sure you want to delete this exam type?"))) {
                        setTypeActionError(null);
                        setDeletingTypeId(type.id);
                        deleteExamTypeMutation.mutate(type.id);
                      }
                    }}
                    className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                    title={t("common.delete", "Delete")}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))
            )}
          </div>

          <DialogFooter className="pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowExamTypesModal(false)}
              className="text-xs"
            >
              {t("common.close", "Close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Exam Type Modal */}
      <Dialog open={showCreateTypeModal} onOpenChange={setShowCreateTypeModal}>
        <DialogContent className="sm:max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Plus className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
              {t("exams.addExamType", "Add Examination Type")}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500 dark:text-slate-400">
              {t(
                "exams.examTypesModalSubtitle",
                "Configure institution-specific examination cycles, term classifications, and board exam indicators."
              )}
            </DialogDescription>
          </DialogHeader>

          {typeActionError && (
            <div className="rounded-md bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
              <span>{typeActionError}</span>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!newTypeName.trim() || !newTypeCode.trim()) {
                setTypeActionError("Name and Code are required.");
                return;
              }
              setTypeActionError(null);
              createExamTypeMutation.mutate({
                name: newTypeName.trim(),
                code: newTypeCode.trim().toUpperCase(),
                is_board_exam: newTypeIsBoard,
                description: newTypeDescription.trim() || undefined,
              });
            }}
            className="space-y-3.5 text-xs mt-2"
          >
            <div>
              <label htmlFor="type-name" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                {t("exams.typeName", "Exam Type Name")} *
              </label>
              <Input
                id="type-name"
                value={newTypeName}
                onChange={(e) => setNewTypeName(e.target.value)}
                placeholder={t("exams.examTypeNameHelp", "e.g. Half-Yearly, Annual Examination, Class Assessment")}
                className="h-9 text-xs"
                required
              />
            </div>

            <div>
              <label htmlFor="type-code" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                {t("exams.typeCode", "Code")} *
              </label>
              <Input
                id="type-code"
                value={newTypeCode}
                onChange={(e) => setNewTypeCode(e.target.value.toUpperCase())}
                placeholder={t("exams.examTypeCodeHelp", "e.g. HY, ANNUAL, CT, PRE_TEST, MODEL_TEST")}
                className="h-9 text-xs font-mono uppercase"
                required
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="type-is-board"
                checked={newTypeIsBoard}
                onChange={(e) => setNewTypeIsBoard(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
              />
              <label htmlFor="type-is-board" className="text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                {t("exams.typeIsBoard", "National Board Exam Pattern (SSC/HSC)")}
              </label>
            </div>

            <div>
              <label htmlFor="type-desc" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                {t("exams.typeDescription", "Description")}
              </label>
              <Input
                id="type-desc"
                value={newTypeDescription}
                onChange={(e) => setNewTypeDescription(e.target.value)}
                placeholder="Optional notes or evaluation details..."
                className="h-9 text-xs"
              />
            </div>

            <DialogFooter className="pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowCreateTypeModal(false)}
                className="text-xs"
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={createExamTypeMutation.isPending}
                className="bg-emerald-800 hover:bg-emerald-900 text-white text-xs"
              >
                {createExamTypeMutation.isPending ? t("common.saving", "Saving...") : t("exams.saveType", "Save Exam Type")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
