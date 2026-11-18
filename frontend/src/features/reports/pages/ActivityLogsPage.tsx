import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Activity,
  Search,
  Filter,
  Calendar,
  Globe,
  User,
  Eye,
  X,
  FileText,
} from "lucide-react";
import {
  reportsApi,
  type ActivityLog,
} from "../api/reportsApi";

export const ActivityLogsPage: React.FC = () => {
  const { t } = useTranslation();

  const [activityTypeFilter, setActivityTypeFilter] = useState<string>("all");
  const [moduleFilter, setModuleFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [selectedActivity, setSelectedActivity] = useState<ActivityLog | null>(null);

  const { data: activitiesData, isLoading } = useQuery({
    queryKey: [
      "activity-logs",
      { activityTypeFilter, moduleFilter, dateFrom, dateTo, searchQuery },
    ],
    queryFn: () =>
      reportsApi.getActivityLogs({
        activity_type: activityTypeFilter !== "all" ? activityTypeFilter : undefined,
        module: moduleFilter.trim() || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: searchQuery.trim() || undefined,
      }),
  });

  const activities = activitiesData?.results || [];

  const handleResetFilters = () => {
    setActivityTypeFilter("all");
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
            <Activity className="w-7 h-7 text-emerald-600" />
            {t("reports.activityLogsTitle", "User Operational Activities")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "reports.activityLogsSubtitle",
              "Real-time stream of administrative actions, user logins, data dispatches, and reports"
            )}
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Activity Type Filter */}
          <div>
            <label htmlFor="activity_type_filter" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.activityType", "Activity Type")}
            </label>
            <select
              id="activity_type_filter"
              value={activityTypeFilter}
              onChange={(e) => setActivityTypeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="all">{t("common.all", "All Activity Types")}</option>
              <option value="login">Login</option>
              <option value="logout">Logout</option>
              <option value="export">Data Export</option>
              <option value="import">Bulk Import</option>
              <option value="report_generate">Report Generate</option>
              <option value="broadcast">SMS/Alert Broadcast</option>
              <option value="status_update">Status Update</option>
            </select>
          </div>

          {/* Module Filter */}
          <div>
            <label htmlFor="act_module_filter" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.module", "System Module")}
            </label>
            <input
              id="act_module_filter"
              type="text"
              placeholder="e.g. auth, reports, sms"
              value={moduleFilter}
              onChange={(e) => setModuleFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Date From */}
          <div>
            <label htmlFor="act_date_from" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.dateFrom", "Date From")}
            </label>
            <input
              id="act_date_from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Date To */}
          <div>
            <label htmlFor="act_date_to" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("reports.dateTo", "Date To")}
            </label>
            <input
              id="act_date_to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Search Query */}
          <div>
            <label htmlFor="act_search_query" className="block text-xs font-semibold text-gray-600 mb-1">
              {t("common.search", "Search Description")}
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
              <input
                id="act_search_query"
                type="text"
                placeholder={t("reports.searchActivityPlaceholder", "Username, keyword...")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
          </div>
        </div>

        {(activityTypeFilter !== "all" || moduleFilter || dateFrom || dateTo || searchQuery) && (
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

      {/* Activities Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading activity stream...")}</p>
          </div>
        ) : activities.length === 0 ? (
          <div className="p-12 text-center">
            <Filter className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("reports.noActivityFound", "No Activity Records Found")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("reports.noActivityDesc", "Recorded user interactions and operations will show here.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("reports.timestamp", "Timestamp")}</th>
                  <th className="px-4 py-3">{t("reports.actor", "Actor")}</th>
                  <th className="px-3 py-3 text-center">{t("reports.type", "Type")}</th>
                  <th className="px-4 py-3">{t("reports.module", "Module")}</th>
                  <th className="px-5 py-3">{t("reports.description", "Description")}</th>
                  <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {activities.map((act) => (
                  <tr key={act.id} className="hover:bg-gray-50/75 transition">
                    <td className="px-5 py-3 whitespace-nowrap text-xs text-gray-600 font-mono">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        {new Date(act.created_at).toLocaleString("en-BD", {
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
                        {act.actor_username || "System"}
                      </div>
                      {act.ip_address && (
                        <div className="text-[11px] text-gray-400 font-mono mt-0.5 flex items-center gap-1">
                          <Globe className="w-3 h-3 text-gray-400" />
                          {act.ip_address}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-center">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 capitalize">
                        {act.activity_type.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-gray-600 font-semibold uppercase">
                      [{act.module}]
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-800 font-medium max-w-md">
                      {act.description}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedActivity(act)}
                        className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" />
                        {t("reports.viewDetails", "Details")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Activity Details */}
      {selectedActivity && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-600" />
                <h3 className="text-lg font-bold text-gray-900">
                  {t("reports.activityDetailsTitle", "Activity Log Record")}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedActivity(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 space-y-2">
                <div>
                  <span className="text-gray-500 block">Description:</span>
                  <p className="font-semibold text-gray-900 text-sm mt-0.5">{selectedActivity.description}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-200">
                  <div>
                    <span className="text-gray-500">Actor:</span>{" "}
                    <span className="font-semibold text-gray-800">{selectedActivity.actor_username || "System"}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Module:</span>{" "}
                    <span className="font-semibold text-gray-800 uppercase">{selectedActivity.module}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">IP Address:</span>{" "}
                    <span className="font-mono text-gray-800">{selectedActivity.ip_address || "—"}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Logged At:</span>{" "}
                    <span className="text-gray-800">{new Date(selectedActivity.created_at).toLocaleString("en-BD")}</span>
                  </div>
                </div>
              </div>

              {selectedActivity.user_agent && (
                <div>
                  <span className="text-gray-500 block mb-1">User Agent Header:</span>
                  <div className="p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-gray-700 font-mono text-[11px] truncate">
                    {selectedActivity.user_agent}
                  </div>
                </div>
              )}

              <div>
                <span className="text-gray-500 block mb-1">Metadata Payload:</span>
                <pre className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-800 font-mono text-[11px] overflow-auto max-h-48 whitespace-pre-wrap">
                  {JSON.stringify(selectedActivity.metadata, null, 2)}
                </pre>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedActivity(null)}
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
