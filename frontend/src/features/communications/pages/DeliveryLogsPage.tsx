import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Send,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  Search,
  RefreshCw,
  Coins,
  MessageSquare,
  Smartphone,
  Eye,
} from "lucide-react";
import {
  communicationsApi,
  type NotificationDelivery,
  type DeliveryStatus,
  type ChannelType,
} from "../api/communicationsApi";

export const DeliveryLogsPage: React.FC = () => {
  const { t } = useTranslation();

  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedDelivery, setSelectedDelivery] = useState<NotificationDelivery | null>(null);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["notification-deliveries", channelFilter, statusFilter, searchQuery],
    queryFn: () =>
      communicationsApi.getDeliveries({
        channel: channelFilter !== "all" ? channelFilter : undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        search: searchQuery || undefined,
      }),
  });

  const deliveries = data?.results || [];
  const totalCount = data?.count || deliveries.length;

  // Compute stat metrics
  const totalSent = deliveries.filter((d) => d.status === "sent" || d.status === "delivered").length;
  const totalDelivered = deliveries.filter((d) => d.status === "delivered").length;
  const totalFailed = deliveries.filter((d) => d.status === "failed").length;
  const totalCost = deliveries
    .reduce((sum, d) => sum + (parseFloat(d.cost_bdt) || 0), 0)
    .toFixed(2);
  const deliveryRate = totalSent > 0 ? Math.round((totalDelivered / totalSent) * 100) : 100;

  const getStatusBadge = (status: DeliveryStatus) => {
    switch (status) {
      case "delivered":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            <CheckCircle className="w-3 h-3 mr-1" />
            {t("communications.statusDelivered", "Delivered")}
          </span>
        );
      case "sent":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <Send className="w-3 h-3 mr-1" />
            {t("communications.statusSent", "Sent")}
          </span>
        );
      case "queued":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
            <Clock className="w-3 h-3 mr-1" />
            {t("communications.statusQueued", "Queued")}
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800">
            <XCircle className="w-3 h-3 mr-1" />
            {t("communications.statusFailed", "Failed")}
          </span>
        );
    }
  };

  const getChannelIcon = (ch: ChannelType) => {
    switch (ch) {
      case "sms":
        return <Smartphone className="w-4 h-4 text-emerald-600" />;
      case "push":
        return <MessageSquare className="w-4 h-4 text-blue-600" />;
      default:
        return <Send className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            {t("communications.deliveryLogsTitle", "Outbound Delivery Logs")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "communications.deliveryLogsSubtitle",
              "Audit trail of SMS dispatches, delivery receipts (DLR), segment billing, and gateway responses"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? "animate-spin" : ""}`} />
          {t("common.refresh", "Refresh")}
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              {t("communications.totalMessages", "Total Dispatched")}
            </p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{totalCount}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
            <Send className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              {t("communications.deliveryRate", "Delivery Success")}
            </p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{deliveryRate}%</p>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
            <CheckCircle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              {t("communications.failures", "Delivery Failures")}
            </p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{totalFailed}</p>
          </div>
          <div className="p-3 bg-rose-50 text-rose-600 rounded-xl">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              {t("communications.spendBDT", "Total Cost")}
            </p>
            <p className="text-2xl font-bold text-gray-900 mt-1">৳{totalCost}</p>
          </div>
          <div className="p-3 bg-amber-50 text-amber-600 rounded-xl">
            <Coins className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">
              {t("communications.filterChannel", "Channel")}
            </label>
            <select
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="all">All Channels</option>
              <option value="sms">SMS</option>
              <option value="push">Push Notification</option>
              <option value="email">Email</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">
              {t("communications.filterStatus", "Delivery Status")}
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="all">All Statuses</option>
              <option value="delivered">Delivered</option>
              <option value="sent">Sent</option>
              <option value="queued">Queued</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder={t("communications.searchRecipient", "Search recipient or mobile...")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Deliveries Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading delivery logs...")}</p>
          </div>
        ) : deliveries.length === 0 ? (
          <div className="p-12 text-center">
            <Send className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("communications.noDeliveriesFound", "No Outbound Messages Found")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("communications.noDeliveriesDesc", "SMS and push notifications sent to students or guardians will appear here with live DLR updates.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("communications.recipient", "Recipient")}</th>
                  <th className="px-4 py-3">{t("communications.channel", "Channel")}</th>
                  <th className="px-4 py-3">{t("communications.content", "Message Title / Snippet")}</th>
                  <th className="px-3 py-3 text-center">{t("communications.segments", "Segments")}</th>
                  <th className="px-3 py-3 text-right">{t("communications.cost", "Cost (৳)")}</th>
                  <th className="px-4 py-3">{t("communications.status", "Status")}</th>
                  <th className="px-4 py-3">{t("communications.timestamp", "Dispatched At")}</th>
                  <th className="px-4 py-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {deliveries.map((delivery) => (
                  <tr key={delivery.id} className="hover:bg-gray-50/75 transition">
                    <td className="px-5 py-3 whitespace-nowrap">
                      <div className="font-medium text-gray-900">{delivery.recipient_name}</div>
                      <div className="text-xs text-gray-500 font-mono">{delivery.recipient_phone}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-xs text-gray-700 capitalize font-medium">
                        {getChannelIcon(delivery.channel)}
                        {delivery.channel}
                      </div>
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <div className="font-medium text-gray-800 text-xs truncate">
                        {delivery.title || "(No Title)"}
                      </div>
                      <div className="text-xs text-gray-500 truncate mt-0.5">
                        {delivery.content}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-center whitespace-nowrap text-xs font-mono font-medium text-gray-700">
                      {delivery.segment_count || 1}
                    </td>
                    <td className="px-3 py-3 text-right whitespace-nowrap text-xs font-mono font-medium text-gray-900">
                      ৳{parseFloat(delivery.cost_bdt || "0").toFixed(2)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {getStatusBadge(delivery.status)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {new Date(delivery.sent_at || delivery.created_at).toLocaleString("en-BD", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedDelivery(delivery)}
                        className="text-gray-400 hover:text-emerald-600 transition p-1"
                        title={t("common.viewDetails", "View Message Details")}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Message Detail Modal */}
      {selectedDelivery && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("communications.deliveryDetailTitle", "Message Audit Details")}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedDelivery(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between py-1.5 border-b border-gray-100">
                <span className="text-gray-500 font-medium">Recipient</span>
                <span className="font-semibold text-gray-900">
                  {selectedDelivery.recipient_name} ({selectedDelivery.recipient_phone})
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100">
                <span className="text-gray-500 font-medium">Status</span>
                <div>{getStatusBadge(selectedDelivery.status)}</div>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100">
                <span className="text-gray-500 font-medium">Provider Reference</span>
                <span className="font-mono text-xs text-gray-700">
                  {selectedDelivery.provider_message_id || "N/A"}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-gray-100">
                <span className="text-gray-500 font-medium">SMS Segments / Cost</span>
                <span className="font-medium text-gray-900">
                  {selectedDelivery.segment_count} segment(s) • ৳{selectedDelivery.cost_bdt}
                </span>
              </div>

              {selectedDelivery.error_message && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                  <span className="font-semibold block mb-0.5">Gateway Error Description:</span>
                  {selectedDelivery.error_message}
                </div>
              )}

              <div>
                <span className="text-xs font-semibold text-gray-500 block mb-1">
                  Message Body ({selectedDelivery.language.toUpperCase()}):
                </span>
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-xs text-gray-800 whitespace-pre-wrap leading-relaxed">
                  {selectedDelivery.content}
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedDelivery(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {t("common.close", "Close")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
