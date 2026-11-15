import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Filter,
  X,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  attendanceApi,
  type AttendanceCorrectionItem,
} from "@/features/attendance/api/attendanceApi";

export default function AttendanceCorrectionsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<"pending" | "approved" | "rejected">("pending");
  const [selectedCorrection, setSelectedCorrection] = useState<{
    item: AttendanceCorrectionItem;
    type: "approve" | "reject";
  } | null>(null);
  const [decisionNotes, setDecisionNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: correctionsData, isLoading } = useQuery({
    queryKey: ["attendance-corrections", statusFilter],
    queryFn: () => attendanceApi.getCorrections({ approval_status: statusFilter }),
  });

  const decideMutation = useMutation({
    mutationFn: ({ id, approved, reason }: { id: string; approved: boolean; reason?: string }) =>
      attendanceApi.decideCorrection(id, {
        approved,
        rejection_reason: reason,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["attendance-corrections"] });
      void queryClient.invalidateQueries({ queryKey: ["daily-attendance"] });
      setSelectedCorrection(null);
      setDecisionNotes("");
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError((err as Error).message || "Decision submission failed.");
    },
  });

  const corrections = correctionsData?.results ?? [];

  const handleDecisionSubmit = () => {
    if (!selectedCorrection) return;

    if (selectedCorrection.type === "reject" && !decisionNotes.trim()) {
      setActionError("A reason is mandatory when declining an attendance correction request.");
      return;
    }

    decideMutation.mutate({
      id: selectedCorrection.item.id,
      approved: selectedCorrection.type === "approve",
      reason: decisionNotes.trim() || undefined,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Link to="/attendance">
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-lg">
              <ArrowLeft className="h-4 w-4 text-slate-600 dark:text-slate-400" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("attendance.correctionsTitle", "Attendance Correction Requests Queue")}
            </h1>
            <p className="text-xs text-slate-500">
              {t(
                "attendance.correctionsSubtitle",
                "Review and authorize manual punch adjustment and missed-scan appeals."
              )}
            </p>
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-slate-400" />
          <div className="inline-flex rounded-lg border border-slate-200 dark:border-slate-800 p-1 bg-slate-50 dark:bg-slate-800/60 text-xs">
            <button
              onClick={() => setStatusFilter("pending")}
              className={`px-3 py-1 rounded-md font-semibold transition-all ${
                statusFilter === "pending"
                  ? "bg-white dark:bg-slate-900 text-amber-700 dark:text-amber-400 shadow-xs"
                  : "text-slate-500 hover:text-slate-900 dark:text-slate-400"
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => setStatusFilter("approved")}
              className={`px-3 py-1 rounded-md font-semibold transition-all ${
                statusFilter === "approved"
                  ? "bg-white dark:bg-slate-900 text-emerald-800 dark:text-emerald-400 shadow-xs"
                  : "text-slate-500 hover:text-slate-900 dark:text-slate-400"
              }`}
            >
              Approved
            </button>
            <button
              onClick={() => setStatusFilter("rejected")}
              className={`px-3 py-1 rounded-md font-semibold transition-all ${
                statusFilter === "rejected"
                  ? "bg-white dark:bg-slate-900 text-rose-700 dark:text-rose-400 shadow-xs"
                  : "text-slate-500 hover:text-slate-900 dark:text-slate-400"
              }`}
            >
              Rejected
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
          </div>
        ) : corrections.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            {statusFilter === "pending"
              ? t("attendance.noPendingCorrections", "No pending attendance correction requests awaiting review.")
              : t("attendance.noCorrections", "No correction records found for this status.")}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">{t("attendance.person", "Individual")}</th>
                  <th className="px-4 py-3 font-semibold font-mono">{t("attendance.targetDate", "Target Date")}</th>
                  <th className="px-4 py-3 font-semibold">{t("attendance.proposedChange", "Requested Change")}</th>
                  <th className="px-4 py-3 font-semibold">{t("attendance.reason", "Reason & Justification")}</th>
                  <th className="px-4 py-3 font-semibold">{t("attendance.requestedBy", "Submitted By")}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t("common.actions", "Decision")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {corrections.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900 dark:text-slate-100">
                        {c.student_name ? `${c.student_name} (Student)` : `${c.staff_name || "Staff"} (Staff)`}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                      {c.target_date}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <span className="line-through text-slate-400 uppercase">{c.status_before}</span>
                        <span>→</span>
                        <span className="font-bold text-emerald-800 dark:text-emerald-400 uppercase">
                          {c.status_after}
                        </span>
                      </div>
                      {(c.time_in_after || c.time_out_after) && (
                        <div className="text-[10px] text-slate-400 pt-0.5">
                          In: {c.time_in_after || "—"} | Out: {c.time_out_after || "—"}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-[220px] truncate">
                      {c.reason}
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {c.requested_by_name || "Self"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {c.approval_status === "pending" ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setActionError(null);
                              setDecisionNotes("");
                              setSelectedCorrection({ item: c, type: "approve" });
                            }}
                            className="h-7 px-2 text-[11px] text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800 border-emerald-300 rounded-md"
                          >
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            {t("common.approve", "Approve")}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setActionError(null);
                              setDecisionNotes("");
                              setSelectedCorrection({ item: c, type: "reject" });
                            }}
                            className="h-7 px-2 text-[11px] text-rose-700 hover:bg-rose-50 hover:text-rose-800 border-rose-300 rounded-md"
                          >
                            <XCircle className="h-3 w-3 mr-1" />
                            {t("common.reject", "Reject")}
                          </Button>
                        </div>
                      ) : (
                        <span
                          className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                            c.approval_status === "approved"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                              : "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                          }`}
                        >
                          {c.approval_status === "approved" && <CheckCircle2 className="h-3 w-3" />}
                          {c.approval_status === "rejected" && <XCircle className="h-3 w-3" />}
                          {c.approval_status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Decision Modal */}
      {selectedCorrection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {selectedCorrection.type === "approve"
                  ? t("attendance.approveCorrectionTitle", "Approve Attendance Adjustment")
                  : t("attendance.rejectCorrectionTitle", "Decline Attendance Adjustment")}
              </h2>
              <button onClick={() => setSelectedCorrection(null)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              {selectedCorrection.type === "approve"
                ? `Confirm attendance status override for ${selectedCorrection.item.student_name || selectedCorrection.item.staff_name} on ${selectedCorrection.item.target_date}.`
                : `Specify reason for declining the adjustment request.`}
            </p>

            {actionError && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                {selectedCorrection.type === "approve" ? "Remarks / Notes (optional)" : "Rejection Reason *"}
              </label>
              <textarea
                value={decisionNotes}
                onChange={(e) => setDecisionNotes(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                placeholder={
                  selectedCorrection.type === "approve"
                    ? "Optional supervisory notes..."
                    : "Mandatory justification for declining..."
                }
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setSelectedCorrection(null)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="sm"
                disabled={decideMutation.isPending}
                onClick={handleDecisionSubmit}
                className={
                  selectedCorrection.type === "approve"
                    ? "bg-emerald-800 hover:bg-emerald-900 text-white"
                    : "bg-rose-700 hover:bg-rose-800 text-white"
                }
              >
                {selectedCorrection.type === "approve" ? "Authorize Override" : "Confirm Rejection"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
