import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertOctagon,
  AlertTriangle,
  Radio,
  Send,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Users,
  Flame,
} from "lucide-react";
import {
  communicationsApi,
  type EmergencySeverity,
} from "../api/communicationsApi";
import {
  emergencyAlertSchema,
  type EmergencyAlertFormData,
} from "../schemas/communicationSchemas";

export const EmergencyAlertsPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [isBroadcastOpen, setIsBroadcastOpen] = useState<boolean>(false);
  const [confirmedRisk, setConfirmedRisk] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch past emergency broadcasts
  const { data: alertsData, isLoading } = useQuery({
    queryKey: ["emergency-alerts"],
    queryFn: () => communicationsApi.getEmergencyAlerts(),
  });

  const alerts = alertsData?.results || [];

  // Broadcast mutation
  const broadcastMutation = useMutation({
    mutationFn: (data: EmergencyAlertFormData) => communicationsApi.broadcastEmergencyAlert(data),
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ["emergency-alerts"] });
      setIsBroadcastOpen(false);
      reset();
      setConfirmedRisk(false);
      setFeedback({
        type: "success",
        message: t(
          "communications.broadcastDispatched",
          `Emergency broadcast "${res.title}" successfully dispatched to ${res.total_recipients || 0} recipients.`
        ),
      });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EmergencyAlertFormData>({
    resolver: zodResolver(emergencyAlertSchema),
    defaultValues: {
      title: "",
      message_bn: "",
      message_en: "",
      severity: "warning",
      channels: ["sms", "push"],
    },
  });

  const selectedChannels = watch("channels") || [];

  const handleChannelToggle = (channel: "sms" | "push" | "email" | "in_app") => {
    if (selectedChannels.includes(channel)) {
      if (selectedChannels.length > 1) {
        setValue(
          "channels",
          selectedChannels.filter((c) => c !== channel)
        );
      }
    } else {
      setValue("channels", [...selectedChannels, channel]);
    }
  };

  const onSubmit = (data: EmergencyAlertFormData) => {
    if (!confirmedRisk) return;
    broadcastMutation.mutate(data);
  };

  const getSeverityBadge = (severity: EmergencySeverity) => {
    switch (severity) {
      case "disaster":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-red-600 text-white animate-pulse">
            <Flame className="w-3.5 h-3.5 mr-1" />
            DISASTER / চরম জরুরি
          </span>
        );
      case "critical":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-orange-600 text-white">
            <AlertOctagon className="w-3.5 h-3.5 mr-1" />
            CRITICAL / অতি জরুরি
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500 text-white">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            WARNING / সতর্কবার্তা
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
            <ShieldAlert className="w-7 h-7 text-rose-600" />
            {t("communications.emergencyTitle", "Campus Emergency Broadcasts")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "communications.emergencySubtitle",
              "Immediate high-priority campus broadcasts overriding quiet hours across SMS and mobile push channels"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setConfirmedRisk(false);
            setIsBroadcastOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 transition"
        >
          <Radio className="w-4 h-4 mr-2 animate-pulse" />
          {t("communications.broadcastNow", "Broadcast Emergency Alert")}
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

      {/* Warning Protocol Card */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl">
        <div className="flex items-start">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-bold text-amber-900">
              Emergency Broadcast Protocol (জরুরি সম্প্রচার বিধিমালা)
            </h4>
            <p className="text-xs text-amber-800 mt-1 leading-relaxed">
              Use this facility strictly for unexpected school closures (cyclone/flood warnings, civic unrest),
              immediate campus evacuation, or urgent safety advisories. Emergency broadcasts bypass quiet hours
              and are delivered with top-priority routing across the active SMS gateways and FCM mobile push notifications.
            </p>
          </div>
        </div>
      </div>

      {/* Broadcast History */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-bold text-gray-900">
            {t("communications.emergencyHistory", "Broadcast Audit Trail")}
          </h2>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading emergency logs...")}</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center">
            <ShieldAlert className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("communications.noEmergencyAlerts", "No Emergency Broadcasts on Record")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("communications.noEmergencyDesc", "All sent emergency alerts and recipient delivery tallies will be safely recorded here.")}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {alerts.map((alert) => (
              <div key={alert.id} className="p-6 hover:bg-gray-50/50 transition">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-3">
                    {getSeverityBadge(alert.severity)}
                    <h3 className="text-lg font-bold text-gray-900">{alert.title}</h3>
                  </div>
                  <span className="text-xs text-gray-500 font-medium">
                    {new Date(alert.sent_at).toLocaleString("en-BD", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="p-3 bg-rose-50/40 border border-rose-100 rounded-lg text-sm text-gray-800">
                    <span className="font-semibold text-rose-950 block text-xs mb-1">বাংলা বার্তা (SMS/Push):</span>
                    {alert.message_bn}
                  </div>
                  {alert.message_en && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700">
                      <span className="font-semibold text-gray-800 block text-xs mb-1">English Message:</span>
                      {alert.message_en}
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-gray-100 text-xs text-gray-500">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1 font-medium text-gray-700">
                      <Users className="w-3.5 h-3.5" />
                      Recipients: {alert.total_recipients || 0}
                    </span>
                    <span className="flex items-center gap-1 text-emerald-600 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Delivered: {alert.successful_deliveries || 0}
                    </span>
                    {alert.failed_deliveries > 0 && (
                      <span className="flex items-center gap-1 text-rose-600 font-medium">
                        <XCircle className="w-3.5 h-3.5" />
                        Failed: {alert.failed_deliveries}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-600">Channels:</span>
                    {alert.channels.map((ch) => (
                      <span key={ch} className="px-2 py-0.5 rounded bg-gray-100 font-mono uppercase text-gray-700 text-xs">
                        {ch}
                      </span>
                    ))}
                    <span className="ml-2 font-medium text-gray-600">
                      By: {alert.sent_by_name || "Admin"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Broadcast Modal */}
      {isBroadcastOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative border-2 border-rose-500 animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-6 h-6 text-rose-600 animate-pulse" />
                <h3 className="text-lg font-bold text-gray-900">
                  {t("communications.emergencyModalTitle", "Initiate Campus Emergency Broadcast")}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsBroadcastOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={(e) => { void handleSubmit(onSubmit)(e); }} className="mt-4 space-y-4">
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 leading-relaxed font-medium">
                ⚠️ Warning: This broadcast triggers instant SMS dispatch across all student guardians and staff phones,
                overriding any active DND / quiet hour policies.
              </div>

              <div>
                <label htmlFor="emergency_title" className="block text-xs font-semibold text-gray-700 mb-1">
                  Alert Title *
                </label>
                <input
                  id="emergency_title"
                  type="text"
                  {...register("title")}
                  placeholder="e.g. Cyclone Alert - Immediate School Closure"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-rose-500 focus:border-rose-500"
                />
                {errors.title && <p className="text-xs text-red-600 mt-1">{errors.title.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="emergency_severity" className="block text-xs font-semibold text-gray-700 mb-1">
                    Severity Level *
                  </label>
                  <select
                    id="emergency_severity"
                    {...register("severity")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-rose-500 focus:border-rose-500"
                  >
                    <option value="warning">Warning / সতর্কবার্তা</option>
                    <option value="critical">Critical / অতি জরুরি</option>
                    <option value="disaster">Disaster / চরম জরুরি</option>
                  </select>
                </div>

                <div>
                  <span className="block text-xs font-semibold text-gray-700 mb-1">
                    Broadcast Channels *
                  </span>
                  <div className="flex gap-2">
                    {(["sms", "push", "email"] as const).map((channel) => (
                      <button
                        key={channel}
                        type="button"
                        onClick={() => handleChannelToggle(channel)}
                        className={`px-3 py-2 rounded-lg text-xs font-medium uppercase border transition ${
                          selectedChannels.includes(channel)
                            ? "bg-rose-50 border-rose-500 text-rose-700 font-bold"
                            : "bg-gray-50 border-gray-200 text-gray-600"
                        }`}
                      >
                        {channel}
                      </button>
                    ))}
                  </div>
                  {errors.channels && (
                    <p className="text-xs text-red-600 mt-1">{errors.channels.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="emergency_message_bn" className="block text-xs font-semibold text-gray-700 mb-1">
                  Bangla Emergency Message (বাংলা বার্তা - SMS & Push) *
                </label>
                <textarea
                  id="emergency_message_bn"
                  {...register("message_bn")}
                  rows={3}
                  placeholder="জরুরি ঘোষণা: ঘূর্ণিঝড়ের সতর্কতার কারণে অদ্য ১৫ নভেম্বর বিদ্যালয়ের সকল কার্যক্রম স্থগিত ঘোষণা করা হলো..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-rose-500 focus:border-rose-500"
                />
                {errors.message_bn && (
                  <p className="text-xs text-red-600 mt-1">{errors.message_bn.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="emergency_message_en" className="block text-xs font-semibold text-gray-700 mb-1">
                  English Message (Optional)
                </label>
                <textarea
                  id="emergency_message_en"
                  {...register("message_en")}
                  rows={2}
                  placeholder="Emergency: Due to adverse weather conditions, all school activities are suspended today..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-rose-500 focus:border-rose-500"
                />
              </div>

              {/* Confirmation check */}
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={confirmedRisk}
                    onChange={(e) => setConfirmedRisk(e.target.checked)}
                    className="mt-1 h-4 w-4 text-rose-600 focus:ring-rose-500 border-gray-300 rounded"
                  />
                  <span className="text-xs font-medium text-gray-800 leading-snug">
                    I verify this is an authentic campus emergency and authorize instant multi-channel broadcast
                    to all guardians and staff members.
                  </span>
                </label>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsBroadcastOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={!confirmedRisk || isSubmitting || broadcastMutation.isPending}
                  className="px-5 py-2 bg-rose-600 text-white rounded-lg text-sm font-bold hover:bg-rose-700 transition disabled:opacity-50 flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  {isSubmitting || broadcastMutation.isPending
                    ? t("common.broadcasting", "Broadcasting...")
                    : t("communications.dispatchBroadcast", "Broadcast Alert Now")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
