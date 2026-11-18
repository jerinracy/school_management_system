import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Calendar,
  CheckCircle2,
  Clock,
  XCircle,
  Plus,
  Filter,
  AlertCircle,
  X,
  FileText,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { staffApi } from "@/features/staff/api/staffApi";
import {
  leaveApplySchema,
  type LeaveApplyFormData,
} from "@/features/staff/schemas/staffSchemas";

export default function LeaveManagementPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"pending" | "all">("pending");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [selectedRequestForAction, setSelectedRequestForAction] = useState<{
    id: string;
    staffName: string;
    type: "approve" | "reject";
  } | null>(null);
  const [actionNotes, setActionNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const { data: leaveTypesData } = useQuery({
    queryKey: ["leave-types"],
    queryFn: () => staffApi.getLeaveTypes(),
  });

  const { data: staffListData } = useQuery({
    queryKey: ["staff-simple-list"],
    queryFn: () => staffApi.getStaffList({ status: "active" }),
    enabled: showApplyModal,
  });

  const {
    data: leaveRequestsData,
    isLoading: isRequestsLoading,
  } = useQuery({
    queryKey: ["leave-requests", activeTab, statusFilter],
    queryFn: () =>
      staffApi.getLeaveRequests({
        status:
          activeTab === "pending"
            ? "pending"
            : statusFilter === "all"
            ? undefined
            : statusFilter,
      }),
  });

  // Apply Form
  const {
    register: registerApply,
    handleSubmit: handleApplySubmit,
    reset: resetApply,
    formState: { errors: applyErrors, isSubmitting: isApplySubmitting },
  } = useForm<LeaveApplyFormData>({
    resolver: zodResolver(leaveApplySchema),
  });

  // Apply Mutation
  const applyMutation = useMutation({
    mutationFn: (data: LeaveApplyFormData) =>
      staffApi.applyLeave({
        staff_id: data.staff_id,
        leave_type_id: data.leave_type_id,
        start_date: data.start_date,
        end_date: data.end_date,
        reason: data.reason,
        emergency_contact_phone: data.emergency_contact_phone || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      resetApply();
      setShowApplyModal(false);
      setActionError(null);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to submit leave application";
      setActionError(msg);
    },
  });

  // Approve Mutation
  const approveMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      staffApi.approveLeave(id, notes),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      setSelectedRequestForAction(null);
      setActionNotes("");
      setActionError(null);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Approval failed";
      setActionError(msg);
    },
  });

  // Reject Mutation
  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      staffApi.rejectLeave(id, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      setSelectedRequestForAction(null);
      setActionNotes("");
      setActionError(null);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Rejection failed";
      setActionError(msg);
    },
  });

  const leaveTypes = leaveTypesData?.results ?? [];
  const staffList = staffListData?.results ?? [];
  const leaveRequests = leaveRequestsData?.results ?? [];

  const handleDecisionSubmit = () => {
    if (!selectedRequestForAction) return;

    if (selectedRequestForAction.type === "approve") {
      approveMutation.mutate({
        id: selectedRequestForAction.id,
        notes: actionNotes,
      });
    } else {
      if (!actionNotes.trim()) {
        setActionError("A reason is required when rejecting a leave request.");
        return;
      }
      rejectMutation.mutate({
        id: selectedRequestForAction.id,
        reason: actionNotes.trim(),
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("staff.leaveTitle", "Leave Management & Approvals")}
          </h1>
          <p className="text-xs text-slate-500">
            {t(
              "staff.leaveSubtitle",
              "Review leave applications, enforce institutional quotas, and approve requests."
            )}
          </p>
        </div>

        <Button
          onClick={() => {
            setActionError(null);
            setShowApplyModal(true);
          }}
          className="gap-2 bg-emerald-800 text-xs hover:bg-emerald-900 text-white rounded-lg h-9 shadow-xs"
        >
          <Plus className="h-4 w-4" />
          <span>{t("staff.applyLeave", "Apply / Grant Leave")}</span>
        </Button>
      </div>

      {/* Leave Types Overview Bar */}
      {leaveTypes.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {leaveTypes.map((type) => (
            <div
              key={type.id}
              className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900 flex items-center justify-between"
            >
              <div>
                <span className="text-[11px] font-bold text-slate-500 block uppercase">
                  {type.code}
                </span>
                <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 line-clamp-1">
                  {type.name}
                </span>
              </div>
              <div className="text-right">
                <span className="text-lg font-mono font-bold text-emerald-800 dark:text-emerald-400">
                  {type.yearly_quota ?? "—"}
                </span>
                <span className="text-[10px] text-slate-400 block">days/yr</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Navigation Tabs & Filter */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-1">
          <button
            onClick={() => setActiveTab("pending")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "pending"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Clock className="h-4 w-4 text-amber-600" />
            {t("staff.pendingApprovals", "Pending Approvals")}
          </button>
          <button
            onClick={() => setActiveTab("all")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "all"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Calendar className="h-4 w-4" />
            {t("staff.allApplications", "All Applications")}
          </button>
        </div>

        {activeTab === "all" && (
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="all">{t("common.allStatuses", "All Statuses")}</option>
              <option value="pending">{t("common.pending", "Pending")}</option>
              <option value="approved">{t("common.approved", "Approved")}</option>
              <option value="rejected">{t("common.rejected", "Rejected")}</option>
              <option value="cancelled">{t("common.cancelled", "Cancelled")}</option>
            </select>
          </div>
        )}
      </div>

      {/* Applications Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
        {isRequestsLoading ? (
          <div className="flex h-48 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
          </div>
        ) : leaveRequests.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            {activeTab === "pending"
              ? t("staff.noPendingLeaves", "No pending leave applications awaiting review.")
              : t("staff.noLeavesFound", "No leave records found.")}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">{t("staff.employee", "Staff Member")}</th>
                  <th className="px-4 py-3 font-semibold">{t("staff.leaveType", "Type")}</th>
                  <th className="px-4 py-3 font-semibold">{t("staff.duration", "Period")}</th>
                  <th className="px-4 py-3 font-semibold text-center">{t("staff.days", "Days")}</th>
                  <th className="px-4 py-3 font-semibold">{t("staff.reason", "Reason")}</th>
                  <th className="px-4 py-3 font-semibold">{t("staff.status", "Status")}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {leaveRequests.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                      {req.staff_name || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-emerald-800 dark:text-emerald-400">
                      {req.leave_type_code}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                      {req.start_date} <span className="text-slate-300">→</span> {req.end_date}
                    </td>
                    <td className="px-4 py-3 text-center font-mono font-bold">
                      {req.days_count}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-[200px] truncate">
                      {req.reason}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                          req.status === "approved"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                            : req.status === "rejected"
                            ? "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                            : "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                        }`}
                      >
                        {req.status === "approved" && <CheckCircle2 className="h-3 w-3" />}
                        {req.status === "rejected" && <XCircle className="h-3 w-3" />}
                        {req.status === "pending" && <Clock className="h-3 w-3" />}
                        {req.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {req.status === "pending" ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setActionError(null);
                              setActionNotes("");
                              setSelectedRequestForAction({
                                id: req.id,
                                staffName: req.staff_name || "Staff",
                                type: "approve",
                              });
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
                              setActionNotes("");
                              setSelectedRequestForAction({
                                id: req.id,
                                staffName: req.staff_name || "Staff",
                                type: "reject",
                              });
                            }}
                            className="h-7 px-2 text-[11px] text-rose-700 hover:bg-rose-50 hover:text-rose-800 border-rose-300 rounded-md"
                          >
                            <XCircle className="h-3 w-3 mr-1" />
                            {t("common.reject", "Reject")}
                          </Button>
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400">
                          {req.approver_name || "Decided"}
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

      {/* Modal: Approve or Reject Confirmation */}
      {selectedRequestForAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {selectedRequestForAction.type === "approve"
                  ? t("staff.approveLeaveTitle", "Approve Leave Request")
                  : t("staff.rejectLeaveTitle", "Reject Leave Request")}
              </h2>
              <button
                onClick={() => setSelectedRequestForAction(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              {selectedRequestForAction.type === "approve"
                ? `Confirm leave approval for ${selectedRequestForAction.staffName}. Quota will be automatically deducted.`
                : `Specify why you are declining the leave request for ${selectedRequestForAction.staffName}.`}
            </p>

            {actionError && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                {selectedRequestForAction.type === "approve"
                  ? t("staff.approvalNotes", "Notes (optional)")
                  : t("staff.rejectionReason", "Rejection Reason *")}
              </label>
              <textarea
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                placeholder={
                  selectedRequestForAction.type === "approve"
                    ? "Optional recommendation remarks..."
                    : "Mandatory reason for rejection..."
                }
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedRequestForAction(null)}
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="sm"
                disabled={approveMutation.isPending || rejectMutation.isPending}
                onClick={handleDecisionSubmit}
                className={
                  selectedRequestForAction.type === "approve"
                    ? "bg-emerald-800 hover:bg-emerald-900 text-white"
                    : "bg-rose-700 hover:bg-rose-800 text-white"
                }
              >
                {selectedRequestForAction.type === "approve"
                  ? t("common.confirmApprove", "Confirm Approval")
                  : t("common.confirmReject", "Confirm Rejection")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Apply / Grant Leave */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-emerald-700" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {t("staff.applyLeaveTitle", "Submit Leave Application")}
                </h2>
              </div>
              <button
                onClick={() => setShowApplyModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {actionError && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <form
              onSubmit={(e) => {
                void handleApplySubmit((data) => applyMutation.mutate(data))(e);
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.selectEmployee", "Select Staff Member")}
                </label>
                <select
                  {...registerApply("staff_id")}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                >
                  <option value="">{t("staff.selectStaffPlaceholder", "Self / Current User")}</option>
                  {staffList.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name_en} ({s.employee_id}) — {s.designation_title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.leaveType", "Leave Type")} *
                </label>
                <select
                  {...registerApply("leave_type_id")}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                >
                  <option value="">{t("staff.selectLeaveType", "Select leave category...")}</option>
                  {leaveTypes.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.code}) — {t.yearly_quota ?? "—"} days/yr
                    </option>
                  ))}
                </select>
                {applyErrors.leave_type_id && (
                  <p className="mt-1 text-[11px] text-rose-600">
                    {applyErrors.leave_type_id.message}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("staff.startDate", "Start Date")} *
                  </label>
                  <Input
                    type="date"
                    {...registerApply("start_date")}
                    className="h-9 text-xs font-mono"
                  />
                  {applyErrors.start_date && (
                    <p className="mt-1 text-[11px] text-rose-600">
                      {applyErrors.start_date.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("staff.endDate", "End Date")} *
                  </label>
                  <Input
                    type="date"
                    {...registerApply("end_date")}
                    className="h-9 text-xs font-mono"
                  />
                  {applyErrors.end_date && (
                    <p className="mt-1 text-[11px] text-rose-600">
                      {applyErrors.end_date.message}
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.emergencyPhone", "Emergency Contact Phone")}
                </label>
                <Input
                  {...registerApply("emergency_contact_phone")}
                  placeholder="+8801XXXXXXXXX"
                  className="h-9 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("staff.reason", "Reason")} *
                </label>
                <textarea
                  {...registerApply("reason")}
                  rows={3}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                  placeholder="Detail the purpose of your leave..."
                />
                {applyErrors.reason && (
                  <p className="mt-1 text-[11px] text-rose-600">
                    {applyErrors.reason.message}
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowApplyModal(false)}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isApplySubmitting || applyMutation.isPending}
                  className="bg-emerald-800 hover:bg-emerald-900 text-white"
                >
                  {isApplySubmitting
                    ? t("common.submitting", "Submitting...")
                    : t("common.submit", "Submit Application")}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
