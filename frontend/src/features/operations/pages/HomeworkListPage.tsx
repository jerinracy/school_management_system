import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  Plus,
  Search,
  CheckCircle,
  XCircle,
  Clock,
  Send,
  FileCheck,
  Calendar,
} from "lucide-react";
import {
  operationsApi,
  type HomeworkStatus,
} from "../api/operationsApi";
import {
  homeworkAssignmentSchema,
  type HomeworkAssignmentFormData,
} from "../schemas/operationsSchemas";

export const HomeworkListPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch assignments
  const { data: assignmentsData, isLoading } = useQuery({
    queryKey: ["homework-assignments", statusFilter, searchQuery],
    queryFn: () =>
      operationsApi.getAssignments({
        status: statusFilter !== "all" ? statusFilter : undefined,
        search: searchQuery || undefined,
      }),
  });

  const assignments = assignmentsData?.results || [];

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: HomeworkAssignmentFormData) =>
      operationsApi.createAssignment({
        ...data,
        status: "draft",
        assigned_at: new Date().toISOString(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["homework-assignments"] });
      setIsCreateOpen(false);
      reset();
      setFeedback({ type: "success", message: t("operations.assignmentCreated", "Homework assignment created successfully") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => operationsApi.publishAssignment(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["homework-assignments"] });
      setFeedback({ type: "success", message: t("operations.assignmentPublished", "Assignment published to students") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const closeMutation = useMutation({
    mutationFn: (id: string) => operationsApi.closeAssignment(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["homework-assignments"] });
      setFeedback({ type: "success", message: t("operations.assignmentClosed", "Assignment submissions closed") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<HomeworkAssignmentFormData>({
    resolver: zodResolver(homeworkAssignmentSchema) as never,
    defaultValues: {
      title: "",
      description: "",
      instructions: "",
      class_level: "Class 10",
      section: "A",
      subject: "Mathematics",
      due_at: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 16),
      max_marks: 25,
      allow_late_submission: true,
    },
  });

  const onSubmit = (data: HomeworkAssignmentFormData) => {
    createMutation.mutate(data);
  };

  const getStatusBadge = (status: HomeworkStatus) => {
    switch (status) {
      case "published":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle className="w-3.5 h-3.5 mr-1" />
            Published
          </span>
        );
      case "closed":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
            <XCircle className="w-3.5 h-3.5 mr-1" />
            Closed
          </span>
        );
      case "draft":
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            <Clock className="w-3.5 h-3.5 mr-1" />
            Draft
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
            <BookOpen className="w-7 h-7 text-emerald-600" />
            {t("operations.homeworkTitle", "Homework & Assignments")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.homeworkSubtitle",
              "Manage academic assignments, track student submission deadlines, and evaluate submitted coursework"
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
          {t("operations.createAssignment", "Create Assignment")}
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

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto">
          {(["all", "published", "draft", "closed"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize whitespace-nowrap transition ${
                statusFilter === status
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {status === "all" ? t("common.allStatus", "All Status") : status}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder={t("operations.searchAssignments", "Search title or subject...")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Assignments Roster */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading assignments...")}</p>
          </div>
        ) : assignments.length === 0 ? (
          <div className="p-12 text-center">
            <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("operations.noAssignmentsFound", "No Homework Assignments Found")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("operations.noAssignmentsDesc", "Issue an academic assignment to track coursework, files, and student grades.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("operations.assignmentTitle", "Assignment Title")}</th>
                  <th className="px-4 py-3">{t("operations.classAndSubject", "Class & Subject")}</th>
                  <th className="px-4 py-3">{t("operations.deadline", "Due Deadline")}</th>
                  <th className="px-3 py-3 text-center">{t("operations.maxMarks", "Max Marks")}</th>
                  <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                  <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {assignments.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/75 transition">
                    <td className="px-5 py-3">
                      <div className="font-semibold text-gray-900">{item.title}</div>
                      <div className="text-xs text-gray-500 line-clamp-1 mt-0.5">{item.description}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="text-xs font-semibold text-gray-800">
                        {item.class_level_name || item.class_level}
                        {item.section_name ? ` • Section ${item.section_name}` : ""}
                      </div>
                      <div className="text-xs text-gray-500">{item.subject_name || item.subject}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                      <div className="flex items-center gap-1 font-medium">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        {new Date(item.due_at).toLocaleDateString("en-BD", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </div>
                      <div className="text-gray-400 text-[11px]">
                        {new Date(item.due_at).toLocaleTimeString("en-BD", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-center whitespace-nowrap font-mono font-bold text-gray-900 text-xs">
                      {item.max_marks}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {getStatusBadge(item.status)}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => { void navigate(`/operations/homework/${item.id}/submissions`); }}
                        className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md transition"
                      >
                        <FileCheck className="w-3.5 h-3.5 mr-1" />
                        {t("operations.viewSubmissions", "Submissions")}
                      </button>

                      {item.status === "draft" && (
                        <button
                          type="button"
                          onClick={() => publishMutation.mutate(item.id)}
                          className="inline-flex items-center text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-md transition"
                        >
                          <Send className="w-3.5 h-3.5 mr-1" />
                          Publish
                        </button>
                      )}

                      {item.status === "published" && (
                        <button
                          type="button"
                          onClick={() => closeMutation.mutate(item.id)}
                          className="inline-flex items-center text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 px-2.5 py-1 rounded-md transition"
                        >
                          Close
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Assignment Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("operations.createAssignmentModal", "Create Homework Assignment")}
              </h3>
              <button
                type="button"
                onClick={() => setIsCreateOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => {
                void handleSubmit(onSubmit)(e);
              }}
              className="mt-4 space-y-4"
            >
              <div>
                <label htmlFor="hw_title" className="block text-xs font-semibold text-gray-700 mb-1">
                  Assignment Title *
                </label>
                <input
                  id="hw_title"
                  type="text"
                  {...register("title")}
                  placeholder="e.g. Chapter 4 Trigonometry Problem Set"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.title && <p className="text-xs text-red-600 mt-1">{errors.title.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="hw_class" className="block text-xs font-semibold text-gray-700 mb-1">
                    Class *
                  </label>
                  <input
                    id="hw_class"
                    type="text"
                    {...register("class_level")}
                    placeholder="e.g. Class 10"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.class_level && <p className="text-xs text-red-600 mt-1">{errors.class_level.message}</p>}
                </div>

                <div>
                  <label htmlFor="hw_subject" className="block text-xs font-semibold text-gray-700 mb-1">
                    Subject *
                  </label>
                  <input
                    id="hw_subject"
                    type="text"
                    {...register("subject")}
                    placeholder="e.g. General Mathematics"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.subject && <p className="text-xs text-red-600 mt-1">{errors.subject.message}</p>}
                </div>
              </div>

              <div>
                <label htmlFor="hw_description" className="block text-xs font-semibold text-gray-700 mb-1">
                  Description & Questions *
                </label>
                <textarea
                  id="hw_description"
                  {...register("description")}
                  rows={3}
                  placeholder="Solve Exercise 4.1 Questions 1 through 10 in your class notebook..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.description && <p className="text-xs text-red-600 mt-1">{errors.description.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="hw_due_at" className="block text-xs font-semibold text-gray-700 mb-1">
                    Due Date & Time *
                  </label>
                  <input
                    id="hw_due_at"
                    type="datetime-local"
                    {...register("due_at")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.due_at && <p className="text-xs text-red-600 mt-1">{errors.due_at.message}</p>}
                </div>

                <div>
                  <label htmlFor="hw_max_marks" className="block text-xs font-semibold text-gray-700 mb-1">
                    Max Marks *
                  </label>
                  <input
                    id="hw_max_marks"
                    type="number"
                    {...register("max_marks")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.max_marks && <p className="text-xs text-red-600 mt-1">{errors.max_marks.message}</p>}
                </div>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="hw_allow_late"
                  {...register("allow_late_submission")}
                  className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
                />
                <label htmlFor="hw_allow_late" className="ml-2 block text-xs font-medium text-gray-700">
                  Allow late submission with automatic flag
                </label>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
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
                    : t("common.create", "Create Assignment")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomeworkListPage;
