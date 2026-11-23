import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Award,
  Banknote,
  Calendar,
  CalendarCheck,
  Clock,
  Database,
  GraduationCap,
  RefreshCw,
  Server,
  Sun,
  Sunset,
  UserCheck,
  Users,
  Wifi,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardKpis } from "@/features/dashboard/api/useDashboardKpis";
import { useHealth } from "@/features/dashboard/api/useHealth";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";
import { formatTimeShort, toLocaleDigits } from "@/lib/format";
import { cn } from "@/lib/utils";

interface CompactStatCardProps {
  label: string;
  value: string;
  badge?: string;
  icon: React.ReactNode;
  loading?: boolean;
}

function CompactStatCard({
  label,
  value,
  badge,
  icon,
  loading = false,
}: CompactStatCardProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-border/80 bg-surface p-3 shadow-2xs" aria-busy="true">
        <div className="flex items-start justify-between gap-1.5">
          <div className="h-8 w-20 animate-pulse rounded bg-slate-200" />
          <div className="h-6 w-6 animate-pulse rounded bg-slate-100" />
        </div>
        <div className="mt-2.5 h-6 w-16 animate-pulse rounded bg-slate-200" />
      </div>
    );
  }

  return (
    <div className="flex flex-col justify-between rounded-lg border border-border/80 bg-surface p-3 shadow-2xs transition-colors hover:border-border-strong hover:shadow-xs">
      <div className="flex items-start justify-between gap-1.5">
        <span className="text-xs font-medium text-ink-muted leading-snug line-clamp-2 min-h-[2.5rem]">
          {label}
        </span>
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-border/60 bg-canvas text-ink-muted">
          {icon}
        </div>
      </div>
      <div className="mt-2 flex items-baseline justify-between gap-1">
        <span className="text-xl font-bold tracking-tight text-ink tabular-nums">{value}</span>
        {badge ? (
          <span className="text-[11px] font-medium text-ink-subtle tabular-nums">{badge}</span>
        ) : null}
      </div>
    </div>
  );
}

export function DashboardHomePage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { selectedBranch, selectedSession } = useAcademicContextStore();

  const {
    data: kpis,
    isLoading: isKpisLoading,
    isError: isKpisError,
    isFetching: isKpisFetching,
    dataUpdatedAt: kpisUpdatedAt,
    refetch: refetchKpis,
  } = useDashboardKpis();

  const {
    data: health,
    isError: isHealthError,
    refetch: refetchHealth,
  } = useHealth();

  const handleRefreshAll = () => {
    void refetchKpis();
    void refetchHealth();
  };

  const isRefreshing = isKpisFetching;

  // Formatted date in Asia/Dhaka context
  const formattedDate = useMemo(() => {
    const now = new Date();
    return now.toLocaleDateString(lang === "bn" ? "bn-BD" : "en-US", {
      weekday: "long",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }, [lang]);

  // Headcount metrics
  const totalStudents = kpis?.headcount?.total_students ?? 0;
  const morningStudents = kpis?.headcount?.morning_shift_students ?? 0;
  const dayStudents = kpis?.headcount?.day_shift_students ?? 0;
  const totalTeachers = kpis?.headcount?.total_teachers ?? 0;
  const totalOfficeStaff = kpis?.headcount?.total_office_staff ?? 0;
  const totalClasses = kpis?.headcount?.total_classes ?? 0;
  const totalSections = kpis?.headcount?.total_sections ?? 0;

  // Shift percentages
  const morningPct = totalStudents > 0 ? Math.round((morningStudents / totalStudents) * 100) : 0;
  const dayPct = totalStudents > 0 ? Math.round((dayStudents / totalStudents) * 100) : 0;

  // Attendance metrics
  const studentRate = kpis?.attendance_rates?.student_present_pct ?? 0;
  const staffRate = kpis?.attendance_rates?.staff_present_pct ?? 0;

  const studentAtt = kpis?.attendance?.student ?? {};
  const studentPresentTotal = (studentAtt.present ?? 0) + (studentAtt.late ?? 0);
  const studentAbsent = studentAtt.absent ?? 0;
  const studentLeave = studentAtt.leave ?? 0;

  const staffAtt = kpis?.attendance?.staff ?? {};
  const staffPresentTotal = (staffAtt.present ?? 0) + (staffAtt.late ?? 0);
  const staffAbsent = staffAtt.absent ?? 0;
  const staffLeave = staffAtt.leave ?? 0;

  // Hardware Devices
  const onlineDevices = kpis?.devices?.online ?? 0;
  const offlineDevices = kpis?.devices?.offline ?? 0;
  const totalDevices = onlineDevices + offlineDevices;

  // System Health
  const isSystemOk = health?.status === "ok";
  const isDbConnected = health?.database === "connected";
  const isRedisConnected = health?.redis === "connected";

  const checkedAt =
    kpisUpdatedAt > 0
      ? `${t("dashboard.lastChecked")}: ${formatTimeShort(new Date(kpisUpdatedAt), lang)}`
      : undefined;

  // Quick Action Buttons
  const QUICK_ACTIONS = [
    {
      to: "/attendance",
      titleKey: "dashboard.quickActions.takeAttendance",
      icon: <CalendarCheck className="h-4 w-4 text-primary" />,
    },
    {
      to: "/students",
      titleKey: "dashboard.quickActions.newAdmission",
      icon: <GraduationCap className="h-4 w-4 text-primary" />,
    },
    {
      to: "/academics/routine",
      titleKey: "dashboard.quickActions.weeklyRoutine",
      icon: <Calendar className="h-4 w-4 text-primary" />,
    },
    {
      to: "/fees",
      titleKey: "dashboard.quickActions.collectFees",
      icon: <Banknote className="h-4 w-4 text-primary" />,
    },
    {
      to: "/staff",
      titleKey: "dashboard.quickActions.staffDirectory",
      icon: <Users className="h-4 w-4 text-primary" />,
    },
  ];

  return (
    <div className="space-y-4">
      {/* 1. Clean Operational Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-ink">
            {t("dashboard.title")}
          </h1>
          <p className="text-xs text-ink-muted">
            <span>{selectedBranch?.name || t("topbar.branchMain", "Main Campus")}</span>
            <span className="mx-1.5 text-border">•</span>
            <span>{selectedSession?.name || t("topbar.sessionLabel", "Academic Session")}</span>
            <span className="mx-1.5 text-border">•</span>
            <span className="tabular-nums">{formattedDate}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {checkedAt ? (
            <span className="hidden sm:inline-block text-[11px] text-ink-subtle tabular-nums">
              {checkedAt}
            </span>
          ) : null}
          <button
            type="button"
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink shadow-2xs transition-colors hover:bg-canvas disabled:opacity-60"
            aria-label={t("dashboard.refresh")}
          >
            <RefreshCw className={cn("h-3 w-3", isRefreshing && "animate-spin")} />
            <span>{isRefreshing ? t("dashboard.refreshing") : t("dashboard.refresh")}</span>
          </button>
        </div>
      </div>

      {/* 2. Error Alert (Only if API or health check fails) */}
      {isKpisError || isHealthError || health?.status === "error" ? (
        <div
          role="alert"
          className="animate-data-fade flex items-start justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-900"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <div>
              <p className="font-semibold">{t("dashboard.states.errorTitle")}</p>
              <p className="mt-0.5 text-rose-800">{t("dashboard.states.errorDetail")}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRefreshAll}
            className="shrink-0 rounded border border-rose-300 bg-white px-2.5 py-1 font-medium text-rose-800 hover:bg-rose-100"
          >
            {t("dashboard.states.retry")}
          </button>
        </div>
      ) : null}

      {/* 3. Compact Executive KPI Cards Grid */}
      <section
        aria-label={t("dashboard.title")}
        className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7"
      >
        <CompactStatCard
          label={t("dashboard.kpis.totalStudents")}
          value={toLocaleDigits(totalStudents, lang)}
          badge={t("dashboard.kpis.activeEnrolled", "Active")}
          icon={<GraduationCap className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />

        <CompactStatCard
          label={t("dashboard.kpis.morningShiftStudents")}
          value={toLocaleDigits(morningStudents, lang)}
          badge={`${toLocaleDigits(morningPct, lang)}%`}
          icon={<Sun className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />

        <CompactStatCard
          label={t("dashboard.kpis.dayShiftStudents")}
          value={toLocaleDigits(dayStudents, lang)}
          badge={`${toLocaleDigits(dayPct, lang)}%`}
          icon={<Sunset className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />

        <CompactStatCard
          label={t("dashboard.kpis.totalTeachers")}
          value={toLocaleDigits(totalTeachers, lang)}
          badge={t("dashboard.kpis.facultyBadge", "Teachers")}
          icon={<UserCheck className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />

        <CompactStatCard
          label={t("dashboard.kpis.totalOfficeStaff")}
          value={toLocaleDigits(totalOfficeStaff, lang)}
          badge={t("dashboard.kpis.staffBadge", "Staff")}
          icon={<Users className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />

        <CompactStatCard
          label={t("dashboard.kpis.studentAttendanceRate")}
          value={`${toLocaleDigits(studentRate, lang)}%`}
          badge={`${toLocaleDigits(studentPresentTotal, lang)} ${t("dashboard.attendance.present")}`}
          icon={<CalendarCheck className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />

        <CompactStatCard
          label={t("dashboard.kpis.staffAttendanceRate")}
          value={`${toLocaleDigits(staffRate, lang)}%`}
          badge={`${toLocaleDigits(staffPresentTotal, lang)} ${t("dashboard.attendance.present")}`}
          icon={<Clock className="h-3.5 w-3.5" />}
          loading={isKpisLoading}
        />
      </section>

      {/* 4. Main Clean Operational Layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left Side: Operations, Attendance & Capacity (8 cols) */}
        <div className="space-y-4 lg:col-span-8">
          {/* Quick Operations Bar */}
          <div className="flex flex-wrap items-center gap-2">
            {QUICK_ACTIONS.map((action) => (
              <Link
                key={action.to}
                to={action.to}
                className="group flex flex-1 min-w-[120px] items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-ink shadow-2xs transition-colors hover:border-primary/40 hover:bg-canvas"
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded border border-border/60 bg-canvas transition-colors group-hover:border-primary/30 group-hover:bg-primary-soft">
                  {action.icon}
                </div>
                <span className="truncate">{t(action.titleKey)}</span>
              </Link>
            ))}
          </div>

          {/* Today's Attendance Overview */}
          <Card className="shadow-2xs">
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold text-ink">
                  {t("dashboard.attendance.title")}
                </CardTitle>
                <Link
                  to="/attendance"
                  className="text-xs font-medium text-primary hover:underline"
                >
                  {t("common.viewAll", "View Details")} →
                </Link>
              </div>
            </CardHeader>
            <CardContent className="pt-0 px-4 pb-3 space-y-3">
              {/* Student Attendance */}
              <div className="rounded-md border border-border/70 bg-slate-50/60 p-2.5">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-semibold text-ink">
                    {t("dashboard.attendance.students")}
                  </span>
                  <span className="font-semibold text-ink tabular-nums">
                    {toLocaleDigits(studentRate, lang)}% (
                    {toLocaleDigits(studentPresentTotal, lang)} / {toLocaleDigits(totalStudents, lang)})
                  </span>
                </div>
                <div className="flex h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    title={`Present: ${studentPresentTotal}`}
                    style={{
                      width: totalStudents > 0 ? `${(studentPresentTotal / totalStudents) * 100}%` : "0%",
                    }}
                    className="bg-emerald-600 transition-all duration-300"
                  />
                  <div
                    title={`Leave: ${studentLeave}`}
                    style={{
                      width: totalStudents > 0 ? `${(studentLeave / totalStudents) * 100}%` : "0%",
                    }}
                    className="bg-amber-500 transition-all duration-300"
                  />
                  <div
                    title={`Absent: ${studentAbsent}`}
                    style={{
                      width: totalStudents > 0 ? `${(studentAbsent / totalStudents) * 100}%` : "0%",
                    }}
                    className="bg-rose-500 transition-all duration-300"
                  />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-ink-muted">
                  <span className="flex items-center gap-1 font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                    {t("dashboard.attendance.present")}: {toLocaleDigits(studentPresentTotal, lang)}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                    {t("dashboard.attendance.absent")}: {toLocaleDigits(studentAbsent, lang)}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                    {t("dashboard.attendance.leave")}: {toLocaleDigits(studentLeave, lang)}
                  </span>
                </div>
              </div>

              {/* Staff Attendance */}
              <div className="rounded-md border border-border/70 bg-slate-50/60 p-2.5">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-semibold text-ink">
                    {t("dashboard.attendance.staff")}
                  </span>
                  <span className="font-semibold text-ink tabular-nums">
                    {toLocaleDigits(staffRate, lang)}% (
                    {toLocaleDigits(staffPresentTotal, lang)} / {toLocaleDigits(totalTeachers + totalOfficeStaff, lang)})
                  </span>
                </div>
                <div className="flex h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    title={`Present: ${staffPresentTotal}`}
                    style={{
                      width: (totalTeachers + totalOfficeStaff) > 0
                        ? `${(staffPresentTotal / (totalTeachers + totalOfficeStaff)) * 100}%`
                        : "0%",
                    }}
                    className="bg-emerald-600 transition-all duration-300"
                  />
                  <div
                    title={`Leave: ${staffLeave}`}
                    style={{
                      width: (totalTeachers + totalOfficeStaff) > 0
                        ? `${(staffLeave / (totalTeachers + totalOfficeStaff)) * 100}%`
                        : "0%",
                    }}
                    className="bg-amber-500 transition-all duration-300"
                  />
                  <div
                    title={`Absent: ${staffAbsent}`}
                    style={{
                      width: (totalTeachers + totalOfficeStaff) > 0
                        ? `${(staffAbsent / (totalTeachers + totalOfficeStaff)) * 100}%`
                        : "0%",
                    }}
                    className="bg-rose-500 transition-all duration-300"
                  />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-ink-muted">
                  <span className="flex items-center gap-1 font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                    {t("dashboard.attendance.present")}: {toLocaleDigits(staffPresentTotal, lang)}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                    {t("dashboard.attendance.absent")}: {toLocaleDigits(staffAbsent, lang)}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                    {t("dashboard.attendance.leave")}: {toLocaleDigits(staffLeave, lang)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Academic Structure & Shift Distribution */}
          <Card className="shadow-2xs">
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold text-ink">
                  {t("dashboard.structure.title")}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                    {toLocaleDigits(totalClasses, lang)} {t("dashboard.structure.classes")}
                  </span>
                  <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                    {toLocaleDigits(totalSections, lang)} {t("dashboard.structure.sections")}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0 px-4 pb-3">
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                <div className="flex items-center justify-between rounded-lg border border-border/80 bg-surface p-2.5">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-100 text-amber-700">
                      <Sun className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-ink">{t("dashboard.structure.morningShift")}</p>
                      <p className="text-[11px] text-ink-muted">
                        {toLocaleDigits(morningStudents, lang)} {t("dashboard.attendance.students")}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-ink tabular-nums">
                    {toLocaleDigits(morningPct, lang)}%
                  </span>
                </div>

                <div className="flex items-center justify-between rounded-lg border border-border/80 bg-surface p-2.5">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-100 text-sky-700">
                      <Sunset className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-ink">{t("dashboard.structure.dayShift")}</p>
                      <p className="text-[11px] text-ink-muted">
                        {toLocaleDigits(dayStudents, lang)} {t("dashboard.attendance.students")}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-ink tabular-nums">
                    {toLocaleDigits(dayPct, lang)}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Side: Schedules, Hardware & System Health (4 cols) */}
        <div className="space-y-4 lg:col-span-4">
          {/* Upcoming Examinations */}
          <Card className="shadow-2xs">
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold text-ink">
                  {t("dashboard.system.upcomingExams")}
                </CardTitle>
                <Link to="/exams" className="text-xs font-medium text-primary hover:underline">
                  {t("common.viewAll", "View")} →
                </Link>
              </div>
            </CardHeader>
            <CardContent className="pt-0 px-4 pb-3 space-y-2">
              <div className="flex items-center justify-between rounded-lg border border-border/80 bg-slate-50/60 p-2.5">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-100 text-amber-700">
                    <Award className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-ink tabular-nums">
                      {toLocaleDigits(kpis?.upcoming_exams_count ?? 0, lang)}
                    </p>
                    <p className="text-[11px] text-ink-muted">{t("dashboard.system.upcomingExams")}</p>
                  </div>
                </div>
                <Link
                  to="/exams"
                  className="rounded border border-border bg-surface px-2 py-1 text-xs font-medium text-ink hover:bg-slate-50"
                >
                  {t("common.view", "View")}
                </Link>
              </div>

              {/* Pending Approvals (Conditional) */}
              {(kpis?.pending_approvals?.attendance_corrections ?? 0) > 0 && (
                <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50/50 p-2.5 text-amber-900">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
                    <div>
                      <p className="text-xs font-semibold">
                        {toLocaleDigits(kpis?.pending_approvals?.attendance_corrections ?? 0, lang)}
                      </p>
                      <p className="text-[11px] text-amber-800">
                        {t("dashboard.system.pendingApprovals")}
                      </p>
                    </div>
                  </div>
                  <Link
                    to="/attendance"
                    className="rounded border border-amber-300 bg-white px-2 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
                  >
                    {t("common.review", "Review")}
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Biometric Terminals Status */}
          <Card className="shadow-2xs">
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold text-ink">
                  {t("dashboard.system.devices")}
                </CardTitle>
                <Link to="/devices" className="text-xs font-medium text-primary hover:underline">
                  {t("common.manage", "Manage")} →
                </Link>
              </div>
            </CardHeader>
            <CardContent className="pt-0 px-4 pb-3">
              <div className="flex items-center justify-between rounded-lg border border-border/80 bg-slate-50/60 p-2.5">
                <div className="flex items-center gap-2">
                  <div className="relative flex h-7 w-7 items-center justify-center rounded-md border border-border/60 bg-canvas text-emerald-700">
                    <Wifi className="h-3.5 w-3.5" />
                    {onlineDevices > 0 && (
                      <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-surface" />
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-ink tabular-nums">
                      {toLocaleDigits(onlineDevices, lang)} / {toLocaleDigits(totalDevices || 1, lang)}
                    </p>
                    <p className="text-[11px] text-ink-muted">
                      {t("dashboard.system.devicesOnline")}
                    </p>
                  </div>
                </div>
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[11px] font-semibold",
                    onlineDevices > 0
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-slate-100 text-slate-700"
                  )}
                >
                  {onlineDevices > 0 ? t("dashboard.states.connected") : t("dashboard.states.degraded")}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Infrastructure Health Status */}
          <Card className="shadow-2xs">
            <CardHeader className="py-2.5 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold text-ink">
                  {t("dashboard.system.health")}
                </CardTitle>
                <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-medium text-ink-muted">
                  v{toLocaleDigits(health?.version ?? "1.0.0", lang)}
                </span>
              </div>
            </CardHeader>
            <CardContent className="pt-0 px-4 pb-3">
              <div className="grid grid-cols-3 gap-1.5 text-center text-[10px]">
                <div className="rounded border border-border/80 bg-slate-50/50 p-1.5">
                  <div className="flex items-center justify-center gap-1 text-ink font-medium">
                    <Activity className="h-3 w-3 text-primary" />
                    <span>API</span>
                  </div>
                  <span
                    className={cn(
                      "mt-0.5 inline-block text-[10px] font-semibold",
                      isSystemOk ? "text-emerald-700" : "text-rose-600"
                    )}
                  >
                    {isSystemOk ? t("dashboard.states.ok") : t("dashboard.states.unreachable")}
                  </span>
                </div>

                <div className="rounded border border-border/80 bg-slate-50/50 p-1.5">
                  <div className="flex items-center justify-center gap-1 text-ink font-medium">
                    <Database className="h-3 w-3 text-primary" />
                    <span>Postgres</span>
                  </div>
                  <span
                    className={cn(
                      "mt-0.5 inline-block text-[10px] font-semibold",
                      isDbConnected ? "text-emerald-700" : "text-rose-600"
                    )}
                  >
                    {isDbConnected ? t("dashboard.states.connected") : "Down"}
                  </span>
                </div>

                <div className="rounded border border-border/80 bg-slate-50/50 p-1.5">
                  <div className="flex items-center justify-center gap-1 text-ink font-medium">
                    <Server className="h-3 w-3 text-primary" />
                    <span>Redis</span>
                  </div>
                  <span
                    className={cn(
                      "mt-0.5 inline-block text-[10px] font-semibold",
                      isRedisConnected ? "text-emerald-700" : "text-rose-600"
                    )}
                  >
                    {isRedisConnected ? t("dashboard.states.connected") : "Down"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
