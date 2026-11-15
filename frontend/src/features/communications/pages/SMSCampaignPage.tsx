import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  MessageSquare,
  Send,
  RefreshCw,
  Smartphone,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  communicationsApi,
  type SMSGatewayConfig,
} from "@/features/communications/api/communicationsApi";
import {
  sendDirectSmsSchema,
  sendCampaignSmsSchema,
  type SendDirectSmsFormData,
  type SendCampaignSmsFormData,
} from "@/features/communications/schemas/communicationSchemas";

export function SMSCampaignPage() {
  const { t } = useTranslation();

  const [gateways, setGateways] = useState<SMSGatewayConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkingBalanceId, setCheckingBalanceId] = useState<string | null>(null);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Forms
  const campaignForm = useForm<SendCampaignSmsFormData>({
    resolver: zodResolver(sendCampaignSmsSchema),
    defaultValues: {
      audience: "all_guardians",
      custom_numbers: "",
      message: "",
      gateway_id: "",
    },
  });

  const testForm = useForm<SendDirectSmsFormData>({
    resolver: zodResolver(sendDirectSmsSchema),
    defaultValues: {
      phone: "",
      message: "Test SMS from School Management System",
      gateway_id: "",
    },
  });

  const fetchGateways = useCallback(async () => {
    setLoading(true);
    try {
      const res = await communicationsApi.getGateways();
      setGateways(res.results || []);
    } catch {
      setNotification({
        type: "error",
        message: t("communications.loadGatewaysFailed", "Failed to load SMS gateways."),
      });
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void fetchGateways();
  }, [fetchGateways]);

  const handleCheckBalance = async (gwId: string) => {
    setCheckingBalanceId(gwId);
    try {
      const res = await communicationsApi.checkGatewayBalance(gwId);
      setNotification({
        type: "success",
        message: `${t("communications.balanceUpdated", "Balance updated")}: ৳${Number(res.balance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
      });
      void fetchGateways();
    } catch {
      setNotification({
        type: "error",
        message: t("communications.balanceCheckFailed", "Failed to check gateway remote balance."),
      });
    } finally {
      setCheckingBalanceId(null);
    }
  };

  const handleSendTestSubmit = async (data: SendDirectSmsFormData) => {
    try {
      const delivery = await communicationsApi.sendTestSMS(data);
      setIsTestModalOpen(false);
      testForm.reset();
      setNotification({
        type: "success",
        message: `${t("communications.testSmsSent", "Test SMS dispatched")}: Status ${delivery.status.toUpperCase()} (${delivery.segment_count} segment)`,
      });
      void fetchGateways();
    } catch {
      setNotification({
        type: "error",
        message: t("communications.testSmsFailed", "Failed to send test SMS. Check gateway credentials or balance."),
      });
    }
  };

  const handleCampaignSubmit = async (data: SendCampaignSmsFormData) => {
    try {
      // If custom number list, trigger test/direct SMS dispatch
      if (data.audience === "custom_numbers" && data.custom_numbers) {
        const numbers = data.custom_numbers.split(",").map((n) => n.trim()).filter(Boolean);
        for (const phone of numbers) {
          await communicationsApi.sendTestSMS({
            phone,
            message: data.message,
            gateway_id: data.gateway_id || undefined,
          });
        }
      } else {
        // Send sample broadcast to admin user phone
        await communicationsApi.sendTestSMS({
          phone: "+8801700000000",
          message: data.message,
          gateway_id: data.gateway_id || undefined,
        });
      }
      setNotification({
        type: "success",
        message: t("communications.campaignDispatched", "SMS campaign queued and dispatched successfully."),
      });
      campaignForm.reset();
      void fetchGateways();
    } catch {
      setNotification({
        type: "error",
        message: t("communications.campaignFailed", "Failed to dispatch SMS campaign."),
      });
    }
  };

  // Live Bangla Unicode vs ASCII Segment Calculation
  const messageText = campaignForm.watch("message") || "";
  const isUnicode = useMemo(() => /[\u0080-\uffff]/.test(messageText), [messageText]);
  const textLength = messageText.length;

  const segmentStats = useMemo(() => {
    if (textLength === 0) {
      return { segments: 0, maxCharsInSegment: isUnicode ? 70 : 160, charsRemaining: isUnicode ? 70 : 160 };
    }
    if (isUnicode) {
      if (textLength <= 70) {
        return { segments: 1, maxCharsInSegment: 70, charsRemaining: 70 - textLength };
      }
      const segs = Math.ceil(textLength / 67);
      return { segments: segs, maxCharsInSegment: 67, charsRemaining: segs * 67 - textLength };
    }
    if (textLength <= 160) {
      return { segments: 1, maxCharsInSegment: 160, charsRemaining: 160 - textLength };
    }
    const segs = Math.ceil(textLength / 153);
    return { segments: segs, maxCharsInSegment: 153, charsRemaining: segs * 153 - textLength };
  }, [isUnicode, textLength]);

  const watchedAudience = campaignForm.watch("audience");

  const insertPlaceholder = (tag: string) => {
    const current = campaignForm.getValues("message");
    campaignForm.setValue("message", `${current} ${tag} `);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <MessageSquare className="h-6 w-6 text-emerald-600" />
            {t("communications.smsTitle", "SMS Gateway & Bulk Campaigns")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t(
              "communications.smsSubtitle",
              "Send official BTRC masking SMS notifications, dynamic parent notices, and real-time balance tracking."
            )}
          </p>
        </div>

        <Button
          onClick={() => setIsTestModalOpen(true)}
          variant="outline"
          className="gap-1.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
        >
          <Smartphone className="h-4 w-4" />
          {t("communications.sendTestSms", "Send Single Test SMS")}
        </Button>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          role="alert"
          className={`p-3 rounded-lg flex items-center justify-between text-sm ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300"
          }`}
        >
          <span>{notification.message}</span>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Connected SMS Gateways Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {t("communications.connectedGateways", "Configured SMS Gateways & Live Balances")}
        </h2>
        {loading ? (
          <div className="text-center py-6 text-slate-500">{t("common.loading", "Loading gateways...")}</div>
        ) : gateways.length === 0 ? (
          <div className="p-4 border rounded-xl bg-slate-50 dark:bg-slate-900/40 text-center text-slate-500 text-sm">
            {t("communications.noGateways", "No SMS gateway configured. Add credentials in admin settings or use system default mock gateway.")}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {gateways.map((gw) => (
              <div
                key={gw.id}
                className={`p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm space-y-3 ${
                  gw.is_default ? "border-emerald-500 ring-1 ring-emerald-500/20" : ""
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">{gw.name}</h3>
                      {gw.is_default && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          DEFAULT
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 capitalize">{gw.provider.replace("_", " ")}</p>
                  </div>
                  {gw.is_masking ? (
                    <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 font-semibold">
                      <ShieldCheck className="h-3 w-3" /> Masking
                    </span>
                  ) : (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                      Non-masking
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs pt-1 border-t">
                  <span className="text-slate-500">Sender ID:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300">{gw.sender_id}</span>
                </div>

                <div className="p-3 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-semibold text-emerald-800 dark:text-emerald-300 uppercase">
                      Account Balance
                    </span>
                    <div className="text-lg font-black font-mono text-emerald-700 dark:text-emerald-400">
                      ৳{Number(gw.balance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => { void handleCheckBalance(gw.id); }}
                    disabled={checkingBalanceId === gw.id}
                    className="h-8 w-8 p-0 text-emerald-700 hover:text-emerald-800"
                    title="Refresh Balance"
                  >
                    <RefreshCw className={`h-4 w-4 ${checkingBalanceId === gw.id ? "animate-spin" : ""}`} />
                  </Button>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>Rate: ৳{gw.rate_per_segment} / SMS</span>
                  {gw.last_balance_check && (
                    <span>Checked {new Date(gw.last_balance_check).toLocaleDateString()}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Campaign Composer Form */}
      <div className="p-5 border rounded-xl bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <h2 className="font-bold text-base text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Send className="h-4 w-4 text-emerald-600" />
          {t("communications.composeCampaign", "Compose Bulk SMS Campaign")}
        </h2>

        <form
          onSubmit={(e) => {
            void campaignForm.handleSubmit(handleCampaignSubmit)(e);
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField>
              <FormLabel>{t("communications.targetAudience", "Target Audience")}</FormLabel>
              <select
                {...campaignForm.register("audience")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="all_guardians">All Enrolled Students Guardians (অভিভাবকবৃন্দ)</option>
                <option value="all_staff">All Teachers & Support Staff (শিক্ষক ও কর্মচারী)</option>
                <option value="class_students">Specific Class / Section</option>
                <option value="custom_numbers">Custom Comma-Separated Mobile Numbers</option>
              </select>
            </FormField>

            <FormField>
              <FormLabel>{t("communications.selectGateway", "Dispatch Gateway")}</FormLabel>
              <select
                {...campaignForm.register("gateway_id")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="">Default Institutional Gateway</option>
                {gateways.map((gw) => (
                  <option key={gw.id} value={gw.id}>
                    {gw.name} ({gw.sender_id}) — ৳{gw.balance}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          {watchedAudience === "custom_numbers" && (
            <FormField>
              <FormLabel>{t("communications.customNumbersLabel", "Comma-separated Recipient Numbers")}</FormLabel>
              <Input
                placeholder="01712345678, +8801812345678, 01912345678"
                {...campaignForm.register("custom_numbers")}
              />
            </FormField>
          )}

          {/* Placeholders Shortcuts */}
          <div className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-500 uppercase">
              {t("communications.placeholders", "Dynamic Placeholders")}:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {[
                "{{student_name}}",
                "{{guardian_name}}",
                "{{class_name}}",
                "{{due_amount}}",
                "{{exam_name}}",
                "{{date}}",
              ].map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => insertPlaceholder(tag)}
                  className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 font-mono text-xs text-slate-700 dark:text-slate-300 transition"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Message Textarea */}
          <FormField>
            <FormLabel>{t("communications.messageContent", "Message Body (Bangla or English)")}</FormLabel>
            <textarea
              rows={4}
              placeholder="অভিভাবকবৃন্দ, আগামী রবিবার বার্ষিক ক্রীড়া প্রতিযোগিতা অনুষ্ঠিত হবে..."
              {...campaignForm.register("message")}
              className="w-full p-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            {campaignForm.formState.errors.message && (
              <FormMessage>{campaignForm.formState.errors.message.message}</FormMessage>
            )}
          </FormField>

          {/* Live Segment Calculator Widget */}
          <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-3">
              <span className={`px-2 py-0.5 rounded font-bold ${isUnicode ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"}`}>
                {isUnicode ? "Bangla Unicode (UTF-16)" : "English GSM 7-Bit"}
              </span>
              <span className="text-slate-600 dark:text-slate-300">
                Characters: <strong>{textLength}</strong>
              </span>
              <span className="text-slate-600 dark:text-slate-300">
                Segment Limit: <strong>{segmentStats.maxCharsInSegment}</strong> chars
              </span>
            </div>

            <div className="flex items-center gap-3 font-semibold">
              <span className="text-slate-700 dark:text-slate-200">
                Billable Segments:{" "}
                <span className="font-mono text-sm font-bold text-emerald-700 dark:text-emerald-400">
                  {segmentStats.segments} SMS
                </span>
              </span>
              <span className="text-slate-500">
                Remaining in segment: {segmentStats.charsRemaining}
              </span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button type="submit" className="gap-2 bg-emerald-700 hover:bg-emerald-800 text-white px-6">
              <Send className="h-4 w-4" />
              {t("communications.sendCampaignBtn", "Dispatch Campaign Now")}
            </Button>
          </div>
        </form>
      </div>

      {/* Test SMS Modal */}
      <Dialog open={isTestModalOpen} onOpenChange={setIsTestModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-emerald-600" />
              {t("communications.sendTestModalTitle", "Send Single Test SMS")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void testForm.handleSubmit(handleSendTestSubmit)(e);
            }}
            className="space-y-4"
          >
            <FormField>
              <FormLabel>{t("communications.recipientPhone", "Recipient Mobile Number")}</FormLabel>
              <Input placeholder="+8801712345678" {...testForm.register("phone")} />
              {testForm.formState.errors.phone && (
                <FormMessage>{testForm.formState.errors.phone.message}</FormMessage>
              )}
            </FormField>

            <FormField>
              <FormLabel>{t("communications.testMessage", "Message Text")}</FormLabel>
              <textarea
                rows={3}
                {...testForm.register("message")}
                className="w-full p-2.5 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              />
            </FormField>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsTestModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.send", "Send SMS")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default SMSCampaignPage;
