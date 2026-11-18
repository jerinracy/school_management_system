import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ShieldCheck,
  Search,
  Filter,
  Eye,
  Calendar,
  X,
  FileCode,
  Globe,
  User,
  Hash,
} from "lucide-react";
import {
  reportsApi,
  type AuditLog,
  type AuditActionType,
} from "../api/reportsApi";

const ACTION_COLORS: Record<AuditActionType, { bg: string; text: string }> = {
  create: { bg: "bg-emerald-100", text: "text-emerald-800" },
  update: { bg: "bg-blue-100", text: "text-blue-800" },
  delete: { bg: "bg-rose-100", text: "text-rose-800" },
  soft_delete: { bg: "bg-orange-100", text: "text-orange-800" },
  login: { bg: "bg-purple-100", text: "text-purple-800" },
  logout: { bg: "bg-gray-100", text: "text-gray-800" },
  login_failed: { bg: "bg-red-100", text: "text-red-800" },
  role_change: { bg: "bg-amber-100", text: "text-amber-800" },
  permission_change: { bg: "bg-indigo-100", text: "text-indigo-800" },
  approve: { bg: "bg-teal-100", text: "text-teal-800" },
  reject: { bg: "bg-rose-100", text: "text-rose-800" },
  override: { bg: "bg-yellow-100", text: "text-yellow-800" },
  export: { bg: "bg-cyan-100", text: "text-cyan-800" },
  consent_change: { bg: "bg-violet-100", text: "text-violet-800" },
  payment: { bg: "bg-emerald-100", text: "text-emerald-800" },
};

export const AuditLogsPage: React.FC = () => {
  const { t } = useTranslation();

  const [actionFilter, setActionFilter] = useState<string>("all");
  const [moduleFilter, setModuleFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const { data: logsData, isLoading } = useQuery({
    queryKey: [
      "audit-logs",
      { actionFilter, moduleFilter, dateFrom, dateTo, searchQuery },
    ],
    queryFn: () =>
      reportsApi.getAuditLogs({
        action: actionFilter !== "all" ? actionFilter : undefined,
        module: moduleFilter.trim() || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: searchQuery.trim() || undefined,
      }),
  });

  const logs = logsData?.results || [];

  const handleResetFilters = () => {
    setActionFilter("all");
    setModuleFilter("");
    setDateFrom("");
    setDateTo("");
    setSearchQuery("");
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <ShieldCheck className="w-7 h-7 text-emerald-600" />
            {t("reports.auditLogsTitle", "Enterprise Audit Trail")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "reports.auditLogsSubtitle",
              "Immutable records of model state modifications, security events, and user authorizations"
            )}
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Action Filter */}
          <div>
            <label htmlFor="action_filter" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.action", "Action Type")}
            </label>
            <select
              id="action_filter"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="all">{t("common.all", "All Actions")}</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
              <option value="login">Login</option>
              <option value="login_failed">Login Failed</option>
              <option value="role_change">Role Change</option>
              <option value="permission_change">Permission Change</option>
              <option value="approve">Approve</option>
              <option value="override">Override</option>
              <option value="export">Export</option>
              <option value="payment">Payment</option>
            </select>
          </div>

          {/* Module Filter */}
          <div>
            <label htmlFor="module_filter" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.module", "System Module")}
            </label>
            <input
              id="module_filter"
              type="text"
              placeholder="e.g. fees, students, auth"
              value={moduleFilter}
              onChange={(e) => setModuleFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Date From */}
          <div>
            <label htmlFor="date_from" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.dateFrom", "Date From")}
            </label>
            <input
              id="date_from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Date To */}
          <div>
            <label htmlFor="date_to" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.dateTo", "Date To")}
            </label>
            <input
              id="date_to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Search Input */}
          <div>
            <label htmlFor="search_query" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("common.search", "Search Actor or Target")}
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
              <input
                id="search_query"
                type="text"
                placeholder={t("reports.searchAuditPlaceholder", "Username, ID, model...")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
          </div>
        </div>

        {(actionFilter !== "all" || moduleFilter || dateFrom || dateTo || searchQuery) && (
          <div className="flex justify-end pt-2 border-t border-gray-100">
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs font-medium text-emerald-600 hover:text-emerald-700"
            >
              {t("common.clearFilters", "Clear All Filters")}
            </button>
          </div>
        )}
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading audit entries...")}</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center">
            <Filter className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("reports.noAuditFound", "No Audit Records Found")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("reports.noAuditDesc", "Security and model modifications will be immutably recorded here.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("reports.timestamp", "Timestamp")}</th>
                  <th className="px-4 py-3">{t("reports.actor", "Actor")}</th>
                  <th className="px-3 py-3 text-center">{t("reports.action", "Action")}</th>
                  <th className="px-4 py-3">{t("reports.target", "Module & Target")}</th>
                  <th className="px-4 py-3">{t("reports.changes", "Changed Fields")}</th>
                  <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {logs.map((log) => {
                  const style = ACTION_COLORS[log.action] || { bg: "bg-gray-100", text: "text-gray-800" };

                  return (
                    <tr key={log.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3 whitespace-nowrap text-xs text-gray-600 font-mono">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-gray-400" />
                          {new Date(log.created_at).toLocaleString("en-BD", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="font-semibold text-gray-900 text-xs flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-gray-400" />
                          {log.actor_username || "System Worker"}
                        </div>
                        {log.ip_address && (
                          <div className="text-[11px] text-gray-400 font-mono mt-0.5 flex items-center gap-1">
                            <Globe className="w-3 h-3 text-gray-400" />
                            {log.ip_address}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold capitalize ${style.bg} ${style.text}`}>
                          {log.action.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <div className="font-semibold text-gray-800">
                          <span className="font-mono text-emerald-700 uppercase mr-1">[{log.module}]</span>
                          {log.target_model}
                        </div>
                        <div className="text-gray-500 font-mono text-[11px] truncate max-w-xs mt-0.5">
                          {log.target_repr || log.target_object_id || "—"}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {log.changed_fields && log.changed_fields.length > 0 ? (
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {log.changed_fields.slice(0, 3).map((f) => (
                              <span key={f} className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-[11px] font-mono">
                                {f}
                              </span>
                            ))}
                            {log.changed_fields.length > 3 && (
                              <span className="text-[11px] text-gray-400">+{log.changed_fields.length - 3}</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedLog(log)}
                          className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition"
                        >
                          <Eye className="w-3.5 h-3.5 mr-1" />
                          {t("reports.inspectDiff", "Inspect Diff")}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Change Diff Inspection */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <FileCode className="w-5 h-5 text-emerald-600" />
                <h3 className="text-lg font-bold text-gray-900">
                  {t("reports.auditDiffTitle", "Audit Record Diff Inspector")}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              {/* Metadata Overview */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-gray-50 rounded-xl border border-gray-200">
                <div>
                  <span className="text-gray-500 block">Actor:</span>
                  <span className="font-semibold text-gray-800">{selectedLog.actor_username || "System"}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Action:</span>
                  <span className="font-semibold text-gray-800 uppercase">{selectedLog.action}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Target:</span>
                  <span className="font-semibold text-gray-800 truncate block">{selectedLog.target_model}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Timestamp:</span>
                  <span className="font-semibold text-gray-800">{new Date(selectedLog.created_at).toLocaleString("en-BD")}</span>
                </div>
              </div>

              {/* Request ID & Client User Agent */}
              <div className="space-y-1 text-gray-600 font-mono bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2">
                  <Hash className="w-3.5 h-3.5 text-gray-400" />
                  <span>Request ID: {selectedLog.request_id || "N/A"}</span>
                </div>
                {selectedLog.user_agent && (
                  <div className="truncate text-[11px] text-gray-400">
                    User-Agent: {selectedLog.user_agent}
                  </div>
                )}
              </div>

              {/* Before vs After Side-by-Side Diffs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <span className="font-semibold text-rose-700 block mb-1">
                    State Before Modification:
                  </span>
                  <pre className="p-3 bg-rose-50/50 border border-rose-200 rounded-lg text-rose-950 font-mono text-[11px] overflow-auto max-h-64 whitespace-pre-wrap">
                    {JSON.stringify(selectedLog.before_data, null, 2)}
                  </pre>
                </div>
                <div>
                  <span className="font-semibold text-emerald-700 block mb-1">
                    State After Modification:
                  </span>
                  <pre className="p-3 bg-emerald-50/50 border border-emerald-200 rounded-lg text-emerald-950 font-mono text-[11px] overflow-auto max-h-64 whitespace-pre-wrap">
                    {JSON.stringify(selectedLog.after_data, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedLog(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
                >
                  {t("common.close", "Close")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
