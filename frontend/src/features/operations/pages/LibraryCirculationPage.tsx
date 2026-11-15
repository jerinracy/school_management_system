import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  BookOpen,
  Plus,
  RefreshCw,
  Clock,
  AlertTriangle,
  RotateCcw,
  Check,
  Coins,
} from "lucide-react";
import {
  operationsApi,
  type BookIssueStatus,
} from "../api/operationsApi";
import {
  issueBookSchema,
  type IssueBookFormData,
} from "../schemas/operationsSchemas";

export const LibraryCirculationPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"issues" | "fines">("issues");
  const [isIssueOpen, setIsIssueOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch active issues
  const { data: issuesData, isLoading: isLoadingIssues } = useQuery({
    queryKey: ["library-issues"],
    queryFn: () => operationsApi.getIssues(),
  });

  const issues = issuesData?.results || [];

  // Fetch fines
  const { data: finesData, isLoading: isLoadingFines } = useQuery({
    queryKey: ["library-fines"],
    queryFn: () => operationsApi.getFines(),
  });

  const fines = finesData?.results || [];

  // Mutations
  const issueMutation = useMutation({
    mutationFn: (data: IssueBookFormData) => operationsApi.issueBook(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library-issues"] });
      setIsIssueOpen(false);
      reset();
      setFeedback({ type: "success", message: t("operations.bookIssued", "Book issued successfully") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const returnMutation = useMutation({
    mutationFn: (copyId: string) => operationsApi.returnBook({ copy: copyId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library-issues"] });
      void queryClient.invalidateQueries({ queryKey: ["library-fines"] });
      setFeedback({ type: "success", message: t("operations.bookReturned", "Book returned to shelf") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const renewMutation = useMutation({
    mutationFn: (copyId: string) => operationsApi.renewBook({ copy: copyId, additional_days: 7 }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library-issues"] });
      setFeedback({ type: "success", message: t("operations.bookRenewed", "Book loan renewed for 7 days") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const payFineMutation = useMutation({
    mutationFn: (fineId: string) =>
      operationsApi.payFine(fineId, { payment_reference: `CASH-${Date.now().toString().slice(-6)}` }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library-fines"] });
      setFeedback({ type: "success", message: t("operations.finePaid", "Fine marked as paid") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const waiveFineMutation = useMutation({
    mutationFn: (fineId: string) =>
      operationsApi.waiveFine(fineId, { waive_reason: "Special Librarian Discretion" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library-fines"] });
      setFeedback({ type: "success", message: t("operations.fineWaived", "Fine waived successfully") });
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
  } = useForm<IssueBookFormData>({
    resolver: zodResolver(issueBookSchema),
    defaultValues: {
      copy: "",
      member: "",
      due_date: new Date(Date.now() + 86400000 * 14).toISOString().split("T")[0],
      remarks: "Regular 14-day student checkout",
    },
  });

  const onSubmit = (data: IssueBookFormData) => {
    issueMutation.mutate(data);
  };

  const getStatusBadge = (status: BookIssueStatus) => {
    switch (status) {
      case "returned":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <Check className="w-3 h-3 mr-1" />
            Returned
          </span>
        );
      case "overdue":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Overdue
          </span>
        );
      case "lost":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
            Lost
          </span>
        );
      case "issued":
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
            <Clock className="w-3 h-3 mr-1" />
            Active Loan
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
            <RotateCcw className="w-7 h-7 text-emerald-600" />
            {t("operations.circulationTitle", "Library Circulation Desk")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.circulationSubtitle",
              "Issue and return book copies, process loan renewals, and manage overdue late fines"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsIssueOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("operations.issueBookBtn", "Issue Book to Member")}
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

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            type="button"
            onClick={() => setActiveTab("issues")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "issues"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t("operations.activeIssuesTab", "Active Book Loans")} ({issues.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("fines")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "fines"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t("operations.overdueFinesTab", "Overdue Fines Ledger")} ({fines.length})
          </button>
        </nav>
      </div>

      {activeTab === "issues" ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoadingIssues ? (
            <div className="p-12 text-center text-gray-500">
              <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
              <p className="text-sm">{t("common.loading", "Loading active checkouts...")}</p>
            </div>
          ) : issues.length === 0 ? (
            <div className="p-12 text-center">
              <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("operations.noActiveIssues", "No Active Loans Found")}
              </h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                {t("operations.noActiveIssuesDesc", "Issue a catalogued book to a student or faculty library card.")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">{t("operations.book", "Book & Accession")}</th>
                    <th className="px-4 py-3">{t("operations.memberCard", "Member Card")}</th>
                    <th className="px-4 py-3">{t("operations.issueDate", "Issue Date")}</th>
                    <th className="px-4 py-3">{t("operations.dueDate", "Due Date")}</th>
                    <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                    <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {issues.map((issue) => (
                    <tr key={issue.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3">
                        <div className="font-semibold text-gray-900">{issue.book_title || "Book Title"}</div>
                        <div className="text-xs text-gray-500 font-mono">
                          Barcode: {issue.barcode || issue.accession_no || issue.copy}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-xs font-semibold text-gray-800">
                        {issue.card_number || issue.member}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                        {new Date(issue.issue_date).toLocaleDateString("en-BD", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-gray-800">
                        {new Date(issue.due_date).toLocaleDateString("en-BD", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {getStatusBadge(issue.status)}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap text-right space-x-2">
                        {issue.status !== "returned" && (
                          <>
                            <button
                              type="button"
                              onClick={() => returnMutation.mutate(issue.copy)}
                              className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md transition"
                            >
                              <Check className="w-3.5 h-3.5 mr-1" />
                              Return
                            </button>
                            <button
                              type="button"
                              onClick={() => renewMutation.mutate(issue.copy)}
                              className="inline-flex items-center text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-md transition"
                            >
                              <RefreshCw className="w-3.5 h-3.5 mr-1" />
                              Renew (+7d)
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Fines Table */
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoadingFines ? (
            <div className="p-12 text-center text-gray-500">
              <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
              <p className="text-sm">{t("common.loading", "Loading overdue fines...")}</p>
            </div>
          ) : fines.length === 0 ? (
            <div className="p-12 text-center">
              <Coins className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("operations.noFinesFound", "No Overdue Fines on Record")}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {t("operations.noFinesDesc", "All library return fines are currently settled.")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">{t("operations.book", "Book Title")}</th>
                    <th className="px-4 py-3">{t("operations.memberCard", "Card Number")}</th>
                    <th className="px-3 py-3 text-center">{t("operations.overdueDays", "Overdue Days")}</th>
                    <th className="px-4 py-3 text-right">{t("operations.amountBDT", "Fine Amount")}</th>
                    <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                    <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {fines.map((fine) => (
                    <tr key={fine.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3 font-semibold text-gray-900">
                        {fine.book_title || "Library Book"}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">
                        {fine.card_number || fine.member}
                      </td>
                      <td className="px-3 py-3 text-center font-mono font-bold text-gray-900 text-xs">
                        {fine.overdue_days} days
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-gray-900 text-xs">
                        ৳{parseFloat(fine.amount).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {fine.status === "paid" ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                            Paid
                          </span>
                        ) : fine.status === "waived" ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
                            Waived
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                            Pending Due
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap text-right space-x-2">
                        {fine.status === "pending" && (
                          <>
                            <button
                              type="button"
                              onClick={() => payFineMutation.mutate(fine.id)}
                              className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md transition"
                            >
                              Collect (৳)
                            </button>
                            <button
                              type="button"
                              onClick={() => waiveFineMutation.mutate(fine.id)}
                              className="inline-flex items-center text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 px-2.5 py-1 rounded-md transition"
                            >
                              Waive
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Issue Book Modal */}
      {isIssueOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("operations.issueBookModal", "Issue Book to Member")}
              </h3>
              <button
                type="button"
                onClick={() => setIsIssueOpen(false)}
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
                <label htmlFor="issue_copy" className="block text-xs font-semibold text-gray-700 mb-1">
                  Book Copy Barcode / Accession ID *
                </label>
                <input
                  id="issue_copy"
                  type="text"
                  {...register("copy")}
                  placeholder="e.g. BK-2026-0042"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.copy && <p className="text-xs text-red-600 mt-1">{errors.copy.message}</p>}
              </div>

              <div>
                <label htmlFor="issue_member" className="block text-xs font-semibold text-gray-700 mb-1">
                  Member Library Card Number *
                </label>
                <input
                  id="issue_member"
                  type="text"
                  {...register("member")}
                  placeholder="e.g. LIB-STU-1004"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.member && <p className="text-xs text-red-600 mt-1">{errors.member.message}</p>}
              </div>

              <div>
                <label htmlFor="issue_due_date" className="block text-xs font-semibold text-gray-700 mb-1">
                  Loan Return Due Date *
                </label>
                <input
                  id="issue_due_date"
                  type="date"
                  {...register("due_date")}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.due_date && <p className="text-xs text-red-600 mt-1">{errors.due_date.message}</p>}
              </div>

              <div>
                <label htmlFor="issue_remarks" className="block text-xs font-semibold text-gray-700 mb-1">
                  Remarks (Optional)
                </label>
                <input
                  id="issue_remarks"
                  type="text"
                  {...register("remarks")}
                  placeholder="e.g. Good condition with plastic jacket"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsIssueOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || issueMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || issueMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("operations.confirmIssue", "Confirm Loan")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LibraryCirculationPage;
