import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Bell,
  Pin,
  Plus,
  Search,
  Calendar,
  Paperclip,
  Eye,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  communicationsApi,
  type Notice,
  type NoticeCategory,
} from "@/features/communications/api/communicationsApi";
import {
  noticeSchema,
  type NoticeFormData,
} from "@/features/communications/schemas/communicationSchemas";

export function NoticeBoardPage() {
  const { t, i18n } = useTranslation();
  const isBn = i18n.language === "bn";

  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedAudience, setSelectedAudience] = useState<string>("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const form = useForm<NoticeFormData>({
    resolver: zodResolver(noticeSchema),
    defaultValues: {
      title_en: "",
      title_bn: "",
      content_en: "",
      content_bn: "",
      category: "general",
      target_audience: "all",
      is_pinned: false,
      is_published: true,
    },
  });

  const fetchNotices = useCallback(async () => {
    setLoading(true);
    try {
      const res = await communicationsApi.getNotices({
        category: selectedCategory === "all" ? undefined : selectedCategory,
        target_audience: selectedAudience === "all" ? undefined : selectedAudience,
        search: search || undefined,
      });
      // Sort pinned notices first
      const sorted = (res.results || []).sort((a, b) => {
        if (a.is_pinned === b.is_pinned) return 0;
        return a.is_pinned ? -1 : 1;
      });
      setNotices(sorted);
    } catch {
      setNotification({
        type: "error",
        message: t("communications.loadNoticesFailed", "Failed to load notices."),
      });
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedAudience, search, t]);

  useEffect(() => {
    void fetchNotices();
  }, [fetchNotices]);

  const handleCreateSubmit = async (data: NoticeFormData) => {
    try {
      await communicationsApi.createNotice({
        ...data,
        publish_date: new Date().toISOString(),
      });
      setIsCreateModalOpen(false);
      form.reset();
      setNotification({
        type: "success",
        message: t("communications.noticePublished", "Notice published successfully."),
      });
      void fetchNotices();
    } catch {
      setNotification({
        type: "error",
        message: t("communications.noticePublishFailed", "Failed to publish notice."),
      });
    }
  };

  const handleTogglePin = async (notice: Notice) => {
    try {
      if (notice.is_pinned) {
        await communicationsApi.unpinNotice(notice.id);
      } else {
        await communicationsApi.pinNotice(notice.id);
      }
      void fetchNotices();
    } catch {
      setNotification({
        type: "error",
        message: t("communications.pinToggleFailed", "Failed to toggle pin state."),
      });
    }
  };

  const openNoticeViewer = (notice: Notice) => {
    setSelectedNotice(notice);
    setIsViewModalOpen(true);
  };

  const getCategoryBadge = (cat: NoticeCategory) => {
    switch (cat) {
      case "academic":
        return <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">Academic</span>;
      case "exam":
        return <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">Exam</span>;
      case "fee":
        return <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">Fee & Billing</span>;
      case "holiday":
        return <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">Holiday</span>;
      case "emergency":
        return <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">Emergency</span>;
      default:
        return <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300">General</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Bell className="h-6 w-6 text-emerald-600" />
            {t("communications.noticesTitle", "Institutional Notice Board")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t(
              "communications.noticesSubtitle",
              "Publish official circulars, exam schedules, holidays, and fee alerts targeted by student grade and audience."
            )}
          </p>
        </div>

        <Button
          onClick={() => setIsCreateModalOpen(true)}
          className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
        >
          <Plus className="h-4 w-4" />
          {t("communications.publishNoticeBtn", "Publish New Circular")}
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

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-3 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("common.search", "Search notices by title or content...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <span>{t("communications.category", "Category")}:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="h-9 px-2 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
            >
              <option value="all">All Categories</option>
              <option value="general">General</option>
              <option value="academic">Academic</option>
              <option value="exam">Examination</option>
              <option value="fee">Fee & Payment</option>
              <option value="holiday">Holiday</option>
              <option value="emergency">Emergency</option>
            </select>
          </label>

          <label className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <span>{t("communications.targetAudience", "Audience")}:</span>
            <select
              value={selectedAudience}
              onChange={(e) => setSelectedAudience(e.target.value)}
              className="h-9 px-2 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
            >
              <option value="all">Entire School</option>
              <option value="guardians">Guardians</option>
              <option value="students">Students</option>
              <option value="teachers">Teachers</option>
              <option value="staff">Staff</option>
              <option value="specific_class">Specific Class</option>
            </select>
          </label>
        </div>
      </div>

      {/* Notices Feed */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">{t("common.loading", "Loading notice board...")}</div>
      ) : notices.length === 0 ? (
        <div className="text-center py-12 border rounded-xl bg-slate-50 dark:bg-slate-900/40">
          <FileText className="h-10 w-10 text-slate-400 mx-auto mb-2" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">
            {t("communications.noNoticesFound", "No active notices matching the filter.")}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {notices.map((n) => (
            <div
              key={n.id}
              className={`p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm transition hover:border-emerald-200 ${
                n.is_pinned ? "border-amber-300 dark:border-amber-700/50 bg-amber-50/20 dark:bg-amber-950/10" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {n.is_pinned && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300">
                        <Pin className="h-3 w-3 fill-amber-700" /> PINNED
                      </span>
                    )}
                    {getCategoryBadge(n.category)}
                    <span className="text-xs font-medium text-slate-500 capitalize">
                      Audience: {n.target_audience.replace("_", " ")}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => openNoticeViewer(n)}
                    className="text-left font-bold text-base text-slate-900 dark:text-slate-100 hover:text-emerald-700 dark:hover:text-emerald-400 cursor-pointer block"
                  >
                    {isBn && n.title_bn ? n.title_bn : n.title_en}
                  </button>

                  <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2">
                    {isBn && n.content_bn ? n.content_bn : n.content_en}
                  </p>

                  <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 pt-1">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {n.publish_date ? new Date(n.publish_date).toLocaleDateString() : ""}
                    </span>
                    <span>By: {n.created_by_name || "School Administration"}</span>
                    {n.attachment && (
                      <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                        <Paperclip className="h-3.5 w-3.5" /> Attachment available
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => { void handleTogglePin(n); }}
                    className={`h-8 w-8 p-0 ${n.is_pinned ? "text-amber-600" : "text-slate-400 hover:text-slate-600"}`}
                    title={n.is_pinned ? "Unpin notice" : "Pin notice to top"}
                  >
                    <Pin className={`h-4 w-4 ${n.is_pinned ? "fill-amber-500" : ""}`} />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => openNoticeViewer(n)}
                    className="h-8 gap-1 text-xs text-emerald-700 hover:text-emerald-800"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    {t("common.view", "View")}
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Publish Notice Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("communications.publishNoticeTitle", "Publish Institutional Circular")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void form.handleSubmit(handleCreateSubmit)(e);
            }}
            className="space-y-4"
          >
            <FormField>
              <FormLabel>{t("communications.titleEn", "Notice Title (English)")}</FormLabel>
              <Input placeholder="e.g. Annual Sports Meet 2026 Schedule" {...form.register("title_en")} />
              {form.formState.errors.title_en && (
                <FormMessage>{form.formState.errors.title_en.message}</FormMessage>
              )}
            </FormField>

            <FormField>
              <FormLabel>{t("communications.titleBn", "Notice Title (Bangla)")}</FormLabel>
              <Input placeholder="e.g. বার্ষিক ক্রীড়া প্রতিযোগিতা ২০২৬ এর সময়সূচি" {...form.register("title_bn")} />
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("communications.category", "Category")}</FormLabel>
                <select
                  {...form.register("category")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="general">General Announcement</option>
                  <option value="academic">Academic Notice</option>
                  <option value="exam">Examination Circular</option>
                  <option value="fee">Fee & Payment Deadline</option>
                  <option value="holiday">Holiday Notice</option>
                  <option value="emergency">Emergency Circular</option>
                </select>
              </FormField>

              <FormField>
                <FormLabel>{t("communications.targetAudience", "Target Audience")}</FormLabel>
                <select
                  {...form.register("target_audience")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="all">Entire School Community</option>
                  <option value="guardians">All Guardians (অভিভাবক)</option>
                  <option value="students">All Students (শিক্ষার্থী)</option>
                  <option value="teachers">All Teachers (শিক্ষক)</option>
                  <option value="staff">All Staff (কর্মচারী)</option>
                </select>
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("communications.contentEn", "Notice Body (English)")}</FormLabel>
              <textarea
                rows={4}
                placeholder="Full notice text..."
                {...form.register("content_en")}
                className="w-full p-2.5 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              />
              {form.formState.errors.content_en && (
                <FormMessage>{form.formState.errors.content_en.message}</FormMessage>
              )}
            </FormField>

            <FormField>
              <FormLabel>{t("communications.contentBn", "Notice Body (Bangla)")}</FormLabel>
              <textarea
                rows={4}
                placeholder="বিজ্ঞপ্তির বিস্তারিত বিবরণ..."
                {...form.register("content_bn")}
                className="w-full p-2.5 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              />
            </FormField>

            <div className="flex items-center gap-4 pt-1">
              <label className="flex items-center gap-2 text-xs font-semibold cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  {...form.register("is_pinned")}
                />
                <span>Pin notice to top of board</span>
              </label>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("communications.publishNow", "Publish Notice")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Notice Modal (Official Circular Format) */}
      <Dialog open={isViewModalOpen} onOpenChange={setIsViewModalOpen}>
        <DialogContent className="max-w-2xl">
          {selectedNotice && (
            <div className="space-y-4">
              <div className="text-center border-b pb-4">
                <h2 className="text-xl font-black text-emerald-800 dark:text-emerald-400">
                  {isBn ? "উত্তরা মডেল হাই স্কুল ও কলেজ" : "Uttara Model High School & College"}
                </h2>
                <p className="text-xs text-slate-500">
                  ইআইআইএন: ১৩৪৫৮২ | সেক্টর-৪, উত্তরা, ঢাকা-১২৩০
                </p>
                <div className="inline-block mt-2 px-3 py-0.5 rounded font-bold text-xs uppercase bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  {selectedNotice.category.toUpperCase()} CIRCULAR
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {isBn && selectedNotice.title_bn ? selectedNotice.title_bn : selectedNotice.title_en}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Published: {new Date(selectedNotice.publish_date || selectedNotice.created_at).toLocaleDateString()}
                  {" • "}Target: {selectedNotice.target_audience.replace("_", " ")}
                </p>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
                {isBn && selectedNotice.content_bn ? selectedNotice.content_bn : selectedNotice.content_en}
              </div>

              <div className="text-right text-xs text-slate-500 pt-4 border-t">
                <p className="font-semibold">{selectedNotice.created_by_name || "Headmaster / Principal"}</p>
                <p>Uttara Model High School & College</p>
              </div>

              <DialogFooter className="pt-2">
                <Button onClick={() => setIsViewModalOpen(false)}>
                  {t("common.close", "Close")}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default NoticeBoardPage;
