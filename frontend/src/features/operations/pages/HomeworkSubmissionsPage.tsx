import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FileCheck,
  ArrowLeft,
  CheckCircle,
  Clock,
  AlertTriangle,
  Award,
  Calendar,
} from "lucide-react";
import {
  operationsApi,
  type HomeworkSubmission,
  type SubmissionStatus,
} from "../api/operationsApi";
import {
  gradeSubmissionSchema,
  type GradeSubmissionFormData,
} from "../schemas/operationsSchemas";

export const HomeworkSubmissionsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selectedSubmission, setSelectedSubmission] = useState<HomeworkSubmission | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch assignment info
  const { data: assignment } = useQuery({
    queryKey: ["homework-detail", id],
    queryFn: () => operationsApi.getAssignmentDetail(id || ""),
    enabled: Boolean(id),
  });

  // Fetch submissions
  const { data: submissionsData, isLoading } = useQuery({
    queryKey: ["homework-submissions", id],
    queryFn: () => operationsApi.getSubmissions({ homework: id }),
    enabled: Boolean(id),
  });

  const submissions = submissionsData?.results || [];

  // Grade mutation
  const gradeMutation = useMutation({
    mutationFn: (data: GradeSubmissionFormData) =>
      operationsApi.gradeSubmission(selectedSubmission?.id || "", data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["homework-submissions", id] });
      setSelectedSubmission(null);
      reset();
      setFeedback({ type: "success", message: t("operations.gradeSaved", "Submission graded successfully") });
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
  } = useForm<GradeSubmissionFormData>({
    resolver: zodResolver(gradeSubmissionSchema) as never,
    defaultValues: {
      marks_obtained: 0,
      feedback: "",
    },
  });

  const handleOpenGrade = (sub: HomeworkSubmission) => {
    setSelectedSubmission(sub);
    reset({
      marks_obtained: sub.marks_obtained ? Number(sub.marks_obtained) : 0,
      feedback: sub.feedback || "",
    });
  };

  const onSubmit = (data: GradeSubmissionFormData) => {
    gradeMutation.mutate(data);
  };

  const getStatusBadge = (status: SubmissionStatus, isLate: boolean) => {
    if (status === "graded") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
          <CheckCircle className="w-3.5 h-3.5 mr-1" />
          Graded
        </span>
      );
    }
    if (isLate) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
          <AlertTriangle className="w-3.5 h-3.5 mr-1" />
          Late Submission
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
        <Clock className="w-3.5 h-3.5 mr-1" />
        Submitted
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => { void navigate("/operations/homework"); }}
            className="inline-flex items-center text-xs font-medium text-emerald-600 hover:text-emerald-700 mb-2 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" />
            {t("common.back", "Back to Assignments")}
          </button>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <FileCheck className="w-7 h-7 text-emerald-600" />
            {assignment?.title || t("operations.submissionsTitle", "Student Submissions")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {assignment?.subject_name ? `${assignment.subject_name} • ` : ""}
            Max Marks: {assignment?.max_marks || "N/A"}
          </p>
        </div>
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

      {/* Submissions Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading submissions...")}</p>
          </div>
        ) : submissions.length === 0 ? (
          <div className="p-12 text-center">
            <FileCheck className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("operations.noSubmissionsFound", "No Student Submissions Yet")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("operations.noSubmissionsDesc", "Submissions will appear here as students turn in their homework.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("operations.student", "Student")}</th>
                  <th className="px-4 py-3">{t("operations.submittedAt", "Submitted At")}</th>
                  <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                  <th className="px-3 py-3 text-center">{t("operations.score", "Marks Obtained")}</th>
                  <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {submissions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-gray-50/75 transition">
                    <td className="px-5 py-3">
                      <div className="font-semibold text-gray-900">{sub.student_name || "Student"}</div>
                      <div className="text-xs text-gray-500 font-mono">{sub.student_code}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                      <div className="flex items-center gap-1 font-medium">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        {new Date(sub.submitted_at).toLocaleString("en-BD", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {getStatusBadge(sub.status, sub.is_late)}
                    </td>
                    <td className="px-3 py-3 text-center whitespace-nowrap font-mono font-bold text-gray-900 text-xs">
                      {sub.marks_obtained !== null && sub.marks_obtained !== undefined
                        ? `${sub.marks_obtained} / ${assignment?.max_marks || ""}`
                        : "—"}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={() => handleOpenGrade(sub)}
                        className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition"
                      >
                        <Award className="w-3.5 h-3.5 mr-1" />
                        {sub.status === "graded" ? "Update Grade" : "Evaluate & Grade"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Grade Submission Modal */}
      {selectedSubmission && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                Grade Submission: {selectedSubmission.student_name}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedSubmission(null)}
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
              {selectedSubmission.text_response && (
                <div>
                  <span className="block text-xs font-semibold text-gray-500 mb-1">
                    Student Submission Text:
                  </span>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-xs text-gray-800 whitespace-pre-wrap">
                    {selectedSubmission.text_response}
                  </div>
                </div>
              )}

              <div>
                <label htmlFor="grade_marks" className="block text-xs font-semibold text-gray-700 mb-1">
                  Marks Obtained (Out of {assignment?.max_marks || 100}) *
                </label>
                <input
                  id="grade_marks"
                  type="number"
                  step="0.5"
                  {...register("marks_obtained")}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.marks_obtained && (
                  <p className="text-xs text-red-600 mt-1">{errors.marks_obtained.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="grade_feedback" className="block text-xs font-semibold text-gray-700 mb-1">
                  Teacher Feedback & Comments
                </label>
                <textarea
                  id="grade_feedback"
                  {...register("feedback")}
                  rows={3}
                  placeholder="Well done, neat handwriting. Review step 4..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setSelectedSubmission(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || gradeMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || gradeMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("operations.saveGrade", "Submit Grade")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomeworkSubmissionsPage;
