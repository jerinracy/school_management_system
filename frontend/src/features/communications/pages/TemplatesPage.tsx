import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FileText,
  Plus,
  Eye,
  Search,
  CheckCircle,
  XCircle,
  Copy,
  Sparkles,
} from "lucide-react";
import { communicationsApi, type NotificationTemplate, type ChannelType } from "../api/communicationsApi";
import {
  notificationTemplateSchema,
  type NotificationTemplateFormData,
} from "../schemas/communicationSchemas";

const COMMON_TAGS = [
  "{{student_name}}",
  "{{roll_number}}",
  "{{class_name}}",
  "{{section_name}}",
  "{{due_amount}}",
  "{{date}}",
  "{{school_name}}",
  "{{portal_link}}",
];

export const TemplatesPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selectedChannel, setSelectedChannel] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [previewTemplate, setPreviewTemplate] = useState<NotificationTemplate | null>(null);
  const [previewLang, setPreviewLang] = useState<"bn" | "en">("bn");
  const [previewVars, setPreviewVars] = useState<Record<string, string>>({
    student_name: "রাহিম ইসলাম",
    class_name: "Class 10",
    section_name: "Padma",
    due_amount: "৳২,৫০০",
    date: "১৫ নভেম্বর ২০২৬",
    school_name: "ঢাকা মডেল একাডেমি",
  });
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch templates
  const { data: templatesData, isLoading } = useQuery({
    queryKey: ["notification-templates", selectedChannel, searchQuery],
    queryFn: () =>
      communicationsApi.getTemplates({
        channel: selectedChannel !== "all" ? selectedChannel : undefined,
        search: searchQuery || undefined,
      }),
  });

  const templates = templatesData?.results || [];

  // Create template mutation
  const createMutation = useMutation({
    mutationFn: (data: NotificationTemplateFormData) => communicationsApi.createTemplate(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notification-templates"] });
      setIsCreateOpen(false);
      reset();
      setFeedback({ type: "success", message: t("communications.templateCreated", "Template created successfully") });
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
  } = useForm<NotificationTemplateFormData>({
    resolver: zodResolver(notificationTemplateSchema),
    defaultValues: {
      name: "",
      code: "",
      channel: "sms",
      subject_template: "",
      body_template_en: "",
      body_template_bn: "",
      is_active: true,
    },
  });

  const bodyBnVal = watch("body_template_bn");
  const bodyEnVal = watch("body_template_en");

  const insertTag = (tag: string, field: "body_template_bn" | "body_template_en") => {
    const current = field === "body_template_bn" ? bodyBnVal : bodyEnVal;
    setValue(field, `${current ? current + " " : ""}${tag}`);
  };

  const onSubmit = (data: NotificationTemplateFormData) => {
    createMutation.mutate(data);
  };

  const getChannelBadge = (ch: ChannelType) => {
    switch (ch) {
      case "sms":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">SMS</span>;
      case "push":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Push</span>;
      case "email":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">Email</span>;
      case "in_app":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">In-App</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">All</span>;
    }
  };

  // Preview replacement
  const renderPreviewText = (template: NotificationTemplate, lang: "bn" | "en") => {
    let text = lang === "bn" ? template.body_template_bn : template.body_template_en;
    Object.entries(previewVars).forEach(([key, val]) => {
      text = text.replace(new RegExp(`{{${key}}}`, "g"), val);
    });
    return text;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            {t("communications.templatesTitle", "Notification Templates")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "communications.templatesSubtitle",
              "Bilingual SMS, Push, and Email templates with dynamic placeholders for academic events"
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
          {t("communications.createTemplate", "Create Template")}
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
          {(["all", "sms", "push", "email", "in_app"] as const).map((channel) => (
            <button
              key={channel}
              type="button"
              onClick={() => setSelectedChannel(channel)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize whitespace-nowrap transition ${
                selectedChannel === channel
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {channel === "all" ? t("common.allChannels", "All Channels") : channel}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder={t("communications.searchTemplates", "Search templates by code or title...")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Templates List */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
          <p className="text-sm">{t("common.loading", "Loading templates...")}</p>
        </div>
      ) : templates.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-base font-medium text-gray-900">
            {t("communications.noTemplatesFound", "No Notification Templates Found")}
          </h3>
          <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
            {t("communications.noTemplatesDesc", "Create standard notification templates for fee alerts, attendance warnings, and notices.")}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {templates.map((tpl) => (
            <div
              key={tpl.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col justify-between hover:border-emerald-300 transition"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  {getChannelBadge(tpl.channel)}
                  {tpl.is_active ? (
                    <span className="flex items-center text-xs text-emerald-600 font-medium">
                      <CheckCircle className="w-3.5 h-3.5 mr-1" />
                      Active
                    </span>
                  ) : (
                    <span className="flex items-center text-xs text-gray-400 font-medium">
                      <XCircle className="w-3.5 h-3.5 mr-1" />
                      Inactive
                    </span>
                  )}
                </div>

                <h3 className="text-base font-semibold text-gray-900 mb-1">{tpl.name}</h3>
                <span className="inline-block font-mono text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded border border-gray-200 mb-3">
                  {tpl.code}
                </span>

                <div className="space-y-2 mt-2">
                  <div className="p-2.5 bg-gray-50 rounded-lg text-xs text-gray-600 line-clamp-3">
                    <span className="font-semibold text-gray-700 block mb-0.5">Bangla:</span>
                    {tpl.body_template_bn}
                  </div>
                  <div className="p-2.5 bg-gray-50 rounded-lg text-xs text-gray-600 line-clamp-3">
                    <span className="font-semibold text-gray-700 block mb-0.5">English:</span>
                    {tpl.body_template_en}
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 mt-4 flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {new Date(tpl.updated_at).toLocaleDateString("en-BD", { day: "numeric", month: "short", year: "numeric" })}
                </span>
                <button
                  type="button"
                  onClick={() => setPreviewTemplate(tpl)}
                  className="inline-flex items-center text-xs font-medium text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition"
                >
                  <Eye className="w-3.5 h-3.5 mr-1.5" />
                  {t("communications.previewAndTest", "Live Preview")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Live Preview Modal */}
      {previewTemplate && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-emerald-600" />
                <h3 className="text-lg font-bold text-gray-900">
                  {previewTemplate.name} ({previewTemplate.code})
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setPreviewTemplate(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {/* Language toggle */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-600">Preview Language:</span>
                <div className="inline-flex rounded-lg border border-gray-200 p-0.5 bg-gray-50">
                  <button
                    type="button"
                    onClick={() => setPreviewLang("bn")}
                    className={`px-3 py-1 text-xs rounded-md font-medium transition ${
                      previewLang === "bn" ? "bg-white text-emerald-700 shadow-sm" : "text-gray-600"
                    }`}
                  >
                    বাংলা (BN)
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewLang("en")}
                    className={`px-3 py-1 text-xs rounded-md font-medium transition ${
                      previewLang === "en" ? "bg-white text-emerald-700 shadow-sm" : "text-gray-600"
                    }`}
                  >
                    English (EN)
                  </button>
                </div>
              </div>

              {/* Sample Variables */}
              <div className="bg-gray-50 p-3 rounded-xl border border-gray-200">
                <span className="text-xs font-semibold text-gray-700 block mb-2">
                  Sample Placeholder Values:
                </span>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label htmlFor="preview_student_name" className="text-gray-500 block">student_name</label>
                    <input
                      id="preview_student_name"
                      type="text"
                      value={previewVars.student_name}
                      onChange={(e) => setPreviewVars({ ...previewVars, student_name: e.target.value })}
                      className="w-full mt-0.5 px-2 py-1 bg-white border border-gray-200 rounded text-xs"
                    />
                  </div>
                  <div>
                    <label htmlFor="preview_due_amount" className="text-gray-500 block">due_amount</label>
                    <input
                      id="preview_due_amount"
                      type="text"
                      value={previewVars.due_amount}
                      onChange={(e) => setPreviewVars({ ...previewVars, due_amount: e.target.value })}
                      className="w-full mt-0.5 px-2 py-1 bg-white border border-gray-200 rounded text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Rendered View */}
              <div>
                <span className="text-xs font-semibold text-gray-700 block mb-1">
                  Rendered Output Preview:
                </span>
                <div className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-gray-800 leading-relaxed font-sans">
                  {renderPreviewText(previewTemplate, previewLang)}
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setPreviewTemplate(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {t("common.close", "Close")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Template Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("communications.createNewTemplate", "Create Notification Template")}
              </h3>
              <button
                type="button"
                onClick={() => setIsCreateOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={(e) => { void handleSubmit(onSubmit)(e); }} className="mt-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="tpl_name" className="block text-xs font-semibold text-gray-700 mb-1">
                    Template Name *
                  </label>
                  <input
                    id="tpl_name"
                    type="text"
                    {...register("name")}
                    placeholder="e.g. Monthly Fee Due Reminder"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
                </div>

                <div>
                  <label htmlFor="tpl_code" className="block text-xs font-semibold text-gray-700 mb-1">
                    Template Code *
                  </label>
                  <input
                    id="tpl_code"
                    type="text"
                    {...register("code")}
                    placeholder="e.g. FEE_DUE_REMINDER"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono uppercase focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.code && <p className="text-xs text-red-600 mt-1">{errors.code.message}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="tpl_channel" className="block text-xs font-semibold text-gray-700 mb-1">
                    Delivery Channel *
                  </label>
                  <select
                    id="tpl_channel"
                    {...register("channel")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  >
                    <option value="sms">SMS</option>
                    <option value="push">Push Notification</option>
                    <option value="in_app">In-App Alert</option>
                    <option value="email">Email</option>
                    <option value="all">Omnichannel (All)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="tpl_subject" className="block text-xs font-semibold text-gray-700 mb-1">
                    Subject Line (Email/Push)
                  </label>
                  <input
                    id="tpl_subject"
                    type="text"
                    {...register("subject_template")}
                    placeholder="e.g. Notice from {{school_name}}"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* Tag inserters */}
              <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                <span className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1.5">
                  <Copy className="w-3.5 h-3.5 text-gray-500" />
                  Click tag to insert placeholder:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {COMMON_TAGS.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => insertTag(tag, "body_template_bn")}
                      className="text-xs font-mono bg-white border border-gray-200 text-emerald-700 px-2 py-0.5 rounded hover:bg-emerald-50 transition"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="tpl_body_bn" className="block text-xs font-semibold text-gray-700 mb-1">
                  Bangla Body Template (বাংলা বার্তা) *
                </label>
                <textarea
                  id="tpl_body_bn"
                  {...register("body_template_bn")}
                  rows={3}
                  placeholder="প্রিয় অভিভাবক, আপনার সন্তান {{student_name}} এর মাসিক ফি {{due_amount}} টাকা বকেয়া রয়েছে..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.body_template_bn && (
                  <p className="text-xs text-red-600 mt-1">{errors.body_template_bn.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="tpl_body_en" className="block text-xs font-semibold text-gray-700 mb-1">
                  English Body Template *
                </label>
                <textarea
                  id="tpl_body_en"
                  {...register("body_template_en")}
                  rows={3}
                  placeholder="Dear Guardian, {{student_name}}'s tuition fee of {{due_amount}} is due on {{date}}..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.body_template_en && (
                  <p className="text-xs text-red-600 mt-1">{errors.body_template_en.message}</p>
                )}
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="tpl_active"
                  {...register("is_active")}
                  className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
                />
                <label htmlFor="tpl_active" className="ml-2 block text-xs font-medium text-gray-700">
                  Activate template immediately
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
                    : t("common.create", "Create Template")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
