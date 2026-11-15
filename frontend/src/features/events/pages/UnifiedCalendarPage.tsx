import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  MapPin,
  List,
  Grid,
  Sparkles,
  Bell,
  Sun,
} from "lucide-react";
import { eventsApi, type UnifiedCalendarItem } from "../api/eventsApi";

interface NewEventFormData {
  title_en: string;
  title_bn: string;
  category: "academic" | "sports" | "annual_function" | "national_day" | "cultural" | "other";
  start_datetime: string;
  end_datetime: string;
  is_all_day: boolean;
  venue: string;
  target_audience: "all" | "students" | "guardians" | "teachers" | "staff" | "specific_class";
}

export const UnifiedCalendarPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const isBangla = i18n.language === "bn";

  const [currentDate, setCurrentDate] = useState<Date>(new Date(2026, 10, 15)); // Nov 2026
  const [filterType, setFilterType] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [isAddOpen, setIsAddOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Month boundaries for API query
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const startDateStr = new Date(year, month, 1).toISOString().split("T")[0];
  const endDateStr = new Date(year, month + 1, 0).toISOString().split("T")[0];

  // Fetch unified calendar items
  const { data: calendarItems = [], isLoading } = useQuery({
    queryKey: ["unified-calendar", startDateStr, endDateStr],
    queryFn: () => eventsApi.getUnifiedCalendar({ start_date: startDateStr, end_date: endDateStr }),
  });

  // Create event mutation
  const createMutation = useMutation({
    mutationFn: (data: NewEventFormData) =>
      eventsApi.createEvent({
        ...data,
        is_published: true,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["unified-calendar"] });
      setIsAddOpen(false);
      reset();
      setFeedback({ type: "success", message: t("events.eventCreated", "Event created successfully") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<NewEventFormData>({
    defaultValues: {
      title_en: "",
      title_bn: "",
      category: "academic",
      start_datetime: new Date().toISOString().slice(0, 16),
      end_datetime: new Date(Date.now() + 3600000 * 2).toISOString().slice(0, 16),
      is_all_day: false,
      venue: "School Auditorium",
      target_audience: "all",
    },
  });

  const onSubmit = (data: NewEventFormData) => {
    createMutation.mutate(data);
  };

  const handlePrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const handleToday = () => {
    setCurrentDate(new Date(2026, 10, 15));
  };

  // Filter items
  const filteredItems = calendarItems.filter((item) => {
    if (filterType === "all") return true;
    return item.source_type === filterType;
  });

  // Calendar calculations
  const firstDayOfWeek = new Date(year, month, 1).getDay(); // 0 is Sunday
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const calendarDays: Array<{ date: number; fullDate: string; isCurrentMonth: boolean }> = [];

  // Pad start
  for (let i = 0; i < firstDayOfWeek; i++) {
    const prevDate = new Date(year, month, -firstDayOfWeek + i + 1);
    calendarDays.push({
      date: prevDate.getDate(),
      fullDate: prevDate.toISOString().split("T")[0] || "",
      isCurrentMonth: false,
    });
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    const dStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    calendarDays.push({
      date: d,
      fullDate: dStr,
      isCurrentMonth: true,
    });
  }

  // Pad end to make 35 or 42 cells
  const remaining = (7 - (calendarDays.length % 7)) % 7;
  for (let i = 1; i <= remaining; i++) {
    const nextDate = new Date(year, month + 1, i);
    calendarDays.push({
      date: nextDate.getDate(),
      fullDate: nextDate.toISOString().split("T")[0] || "",
      isCurrentMonth: false,
    });
  }

  const getSourceIcon = (src: UnifiedCalendarItem["source_type"]) => {
    switch (src) {
      case "holiday":
        return <Sun className="w-3.5 h-3.5 text-amber-500" />;
      case "notice":
        return <Bell className="w-3.5 h-3.5 text-blue-500" />;
      case "event":
      default:
        return <Sparkles className="w-3.5 h-3.5 text-emerald-600" />;
    }
  };

  const getSourceBadgeClass = (src: UnifiedCalendarItem["source_type"]) => {
    switch (src) {
      case "holiday":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "notice":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "event":
      default:
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
    }
  };

  const monthNamesEn = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const monthNamesBn = [
    "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
  ];

  const currentMonthLabel = isBangla
    ? `${monthNamesBn[month]} ${year}`
    : `${monthNamesEn[month]} ${year}`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <CalendarIcon className="w-7 h-7 text-emerald-600" />
            {t("events.calendarTitle", "Unified Academic Calendar")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "events.calendarSubtitle",
              "Consolidated institutional view of school events, public holidays, examinations, and notice circulations"
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg border border-gray-300 bg-white p-0.5 shadow-sm">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-md text-sm transition ${
                viewMode === "grid" ? "bg-emerald-50 text-emerald-700" : "text-gray-500 hover:text-gray-700"
              }`}
              title="Month Grid View"
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded-md text-sm transition ${
                viewMode === "list" ? "bg-emerald-50 text-emerald-700" : "text-gray-500 hover:text-gray-700"
              }`}
              title="Agenda List View"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          <button
            type="button"
            onClick={() => {
              reset();
              setIsAddOpen(true);
            }}
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t("events.addEvent", "Add Event")}
          </button>
        </div>
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

      {/* Month Navigation & Source Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handlePrevMonth}
            className="p-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h2 className="text-lg font-bold text-gray-900 min-w-[170px] text-center">
            {currentMonthLabel}
          </h2>
          <button
            type="button"
            onClick={handleNextMonth}
            className="p-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleToday}
            className="px-2.5 py-1 text-xs font-medium border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            {t("events.today", "Today")}
          </button>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto">
          {(
            [
              { id: "all", label: "All Items" },
              { id: "event", label: "Academic Events" },
              { id: "holiday", label: "Holidays" },
              { id: "notice", label: "Notices" },
            ] as const
          ).map((src) => (
            <button
              key={src.id}
              type="button"
              onClick={() => setFilterType(src.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                filterType === src.id
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {src.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid or List View */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
          <p className="text-sm">{t("common.loading", "Loading calendar schedule...")}</p>
        </div>
      ) : viewMode === "grid" ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Day Headers */}
          <div className="grid grid-cols-7 border-b border-gray-200 bg-gray-50 text-center text-xs font-semibold text-gray-600 uppercase py-2.5">
            <div>Sun / রবি</div>
            <div>Mon / সোম</div>
            <div>Tue / মঙ্গল</div>
            <div>Wed / বুধ</div>
            <div>Thu / বৃহঃ</div>
            <div className="text-rose-600">Fri / শুক্র</div>
            <div className="text-rose-600">Sat / শনি</div>
          </div>

          {/* Grid Cells */}
          <div className="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-gray-100">
            {calendarDays.map((cell, idx) => {
              const dayItems = filteredItems.filter((item) => {
                const itemDate = item.start ? item.start.split("T")[0] : "";
                return itemDate === cell.fullDate;
              });

              const isWeekend = idx % 7 === 5 || idx % 7 === 6;

              return (
                <div
                  key={cell.fullDate + idx}
                  className={`min-h-[105px] p-2 flex flex-col justify-between transition ${
                    !cell.isCurrentMonth
                      ? "bg-gray-50/50 text-gray-400"
                      : isWeekend
                      ? "bg-rose-50/20"
                      : "bg-white"
                  }`}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span
                      className={`text-xs font-semibold rounded-full w-5 h-5 flex items-center justify-center ${
                        cell.fullDate === "2026-11-15"
                          ? "bg-emerald-600 text-white"
                          : isWeekend
                          ? "text-rose-600"
                          : "text-gray-700"
                      }`}
                    >
                      {cell.date}
                    </span>
                    {dayItems.length > 2 && (
                      <span className="text-[10px] text-gray-400 font-mono">
                        +{dayItems.length - 2}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1 overflow-hidden">
                    {dayItems.slice(0, 2).map((item) => (
                      <div
                        key={item.id}
                        className={`text-[11px] leading-tight px-1.5 py-0.5 rounded border truncate flex items-center gap-1 ${getSourceBadgeClass(
                          item.source_type
                        )}`}
                        title={isBangla ? item.title_bn || item.title_en : item.title_en}
                      >
                        {getSourceIcon(item.source_type)}
                        <span className="truncate">
                          {isBangla ? item.title_bn || item.title_en : item.title_en}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Agenda List View */
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm divide-y divide-gray-200 overflow-hidden">
          {filteredItems.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <CalendarIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("events.noEventsThisMonth", "No Events or Holidays Scheduled")}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {t("events.noEventsDesc", "Check other months or add a new school event.")}
              </p>
            </div>
          ) : (
            filteredItems.map((item) => (
              <div key={item.id} className="p-4 hover:bg-gray-50 transition flex items-start gap-4">
                <div className="flex-shrink-0 text-center w-16 bg-gray-50 p-2 rounded-xl border border-gray-200">
                  <span className="text-xs uppercase font-semibold text-gray-500 block">
                    {new Date(item.start).toLocaleDateString("en-BD", { month: "short" })}
                  </span>
                  <span className="text-xl font-bold text-gray-900 block leading-tight">
                    {new Date(item.start).getDate()}
                  </span>
                </div>

                <div className="flex-grow">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getSourceBadgeClass(
                        item.source_type
                      )}`}
                    >
                      {getSourceIcon(item.source_type)}
                      {item.source_type.toUpperCase()}
                    </span>
                    <h3 className="text-base font-semibold text-gray-900">
                      {isBangla ? item.title_bn || item.title_en : item.title_en}
                    </h3>
                  </div>

                  {item.description && (
                    <p className="text-xs text-gray-600 line-clamp-2 mt-1">{item.description}</p>
                  )}

                  <div className="flex items-center gap-4 text-xs text-gray-500 mt-2">
                    {item.venue && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-gray-400" />
                        {item.venue}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-gray-400" />
                      {item.is_all_day
                        ? "All Day"
                        : new Date(item.start).toLocaleTimeString("en-BD", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Add Event Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("events.addNewEvent", "Add Academic Event")}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={(e) => { void handleSubmit(onSubmit)(e); }} className="mt-4 space-y-4">
              <div>
                <label htmlFor="cal_title_en" className="block text-xs font-semibold text-gray-700 mb-1">
                  Event Title (English) *
                </label>
                <input
                  id="cal_title_en"
                  type="text"
                  required
                  {...register("title_en")}
                  placeholder="e.g. Annual Sports Competition 2026"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              <div>
                <label htmlFor="cal_title_bn" className="block text-xs font-semibold text-gray-700 mb-1">
                  Event Title (বাংলা)
                </label>
                <input
                  id="cal_title_bn"
                  type="text"
                  {...register("title_bn")}
                  placeholder="যেমন: বার্ষিক ক্রীড়া প্রতিযোগিতা ২০২৬"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="cal_category" className="block text-xs font-semibold text-gray-700 mb-1">
                    Event Category *
                  </label>
                  <select
                    id="cal_category"
                    {...register("category")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  >
                    <option value="academic">Academic / পরীক্ষা সংক্রান্ত</option>
                    <option value="sports">Sports / খেলাধুলা</option>
                    <option value="annual_function">Annual Function / বার্ষিক অনুষ্ঠান</option>
                    <option value="national_day">National Day / জাতীয় দিবস</option>
                    <option value="cultural">Cultural / সাংস্কৃতিক</option>
                    <option value="other">Other / অন্যান্য</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="cal_venue" className="block text-xs font-semibold text-gray-700 mb-1">
                    Venue / স্থান
                  </label>
                  <input
                    id="cal_venue"
                    type="text"
                    {...register("venue")}
                    placeholder="e.g. School Playground"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="cal_start_datetime" className="block text-xs font-semibold text-gray-700 mb-1">
                    Start Date & Time *
                  </label>
                  <input
                    id="cal_start_datetime"
                    type="datetime-local"
                    required
                    {...register("start_datetime")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label htmlFor="cal_end_datetime" className="block text-xs font-semibold text-gray-700 mb-1">
                    End Date & Time *
                  </label>
                  <input
                    id="cal_end_datetime"
                    type="datetime-local"
                    required
                    {...register("end_datetime")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="event_all_day"
                  {...register("is_all_day")}
                  className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
                />
                <label htmlFor="event_all_day" className="ml-2 block text-xs font-medium text-gray-700">
                  All day event (সারাদিনব্যাপী)
                </label>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
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
                    : t("common.create", "Schedule Event")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
