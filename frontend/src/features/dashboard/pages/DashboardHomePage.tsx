import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Award,
  Banknote,
  CalendarCheck,
  Database,
  GraduationCap,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { KpiCard, type KpiTone } from "@/components/ui/KpiCard";
import { useHealth } from "@/features/dashboard/api/useHealth";
import { formatTimeShort, toLocaleDigits } from "@/lib/format";
import { cn } from "@/lib/utils";

const MODULE_LINKS = [
  {
    to: "/students",
    titleKey: "dashboard.modules.students.title",
    descKey: "dashboard.modules.students.desc",
    icon: <GraduationCap className="h-4 w-4 text-primary" />,
  },
  {
    to: "/attendance",
    titleKey: "dashboard.modules.attendance.title",
    descKey: "dashboard.modules.attendance.desc",
    icon: <CalendarCheck className="h-4 w-4 text-primary" />,
  },
  {
    to: "/exams",
    titleKey: "dashboard.modules.exams.title",
    descKey: "dashboard.modules.exams.desc",
    icon: <Award className="h-4 w-4 text-academic-amber" />,
  },
  {
    to: "/fees",
    titleKey: "dashboard.modules.fees.title",
    descKey: "dashboard.modules.fees.desc",
    icon: <Banknote className="h-4 w-4 text-academic-navy" />,
  },
];

export function DashboardHomePage() {
  const { t, i18n } = useTranslation();
  const { data, isLoading, isError, isFetching, dataUpdatedAt, refetch } = useHealth();

  const lang = i18n.language;

  const apiTone: KpiTone = isError
    ? "danger"
    : data?.status === "ok"
      ? "success"
      : data?.status === "degraded"
        ? "warning"
        : "neutral";

  const dbTone: KpiTone = isError
    ? "danger"
    : data?.database === "connected"
      ? "success"
      : "danger";

  const redisTone: KpiTone = isError
    ? "danger"
    : data?.redis === "connected"
      ? "success"
      : "warning";

  const statusText = isError
    ? t("dashboard.states.unreachable")
    : data?.status === "ok"
      ? t("dashboard.states.ok")
      : t("dashboard.states.degraded");

  const dbText = data?.database === "connected" ? t("dashboard.states.connected") : statusText;
  const redisText =
    data?.redis === "connected" ? t("dashboard.states.connected") : t("dashboard.states.degraded");

  const checkedAt =
    dataUpdatedAt > 0
      ? `${t("dashboard.lastChecked")}: ${formatTimeShort(new Date(dataUpdatedAt), lang)}`
      : undefined;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-ink">{t("dashboard.title")}</h1>
          <p className="text-xs text-ink-muted">{t("dashboard.subtitle")}</p>
        </div>

        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink shadow-sm transition-colors hover:bg-slate-50 disabled:opacity-60"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
          <span>{isFetching ? t("dashboard.refreshing") : t("dashboard.refresh")}</span>
        </button>
      </div>

      {isError ? (
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
            onClick={() => void refetch()}
            className="shrink-0 rounded border border-rose-300 bg-white px-2.5 py-1 font-medium text-rose-800 hover:bg-rose-100"
          >
            {t("dashboard.states.retry")}
          </button>
        </div>
      ) : null}

      <section aria-label={t("dashboard.title")} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label={t("dashboard.kpis.apiStatus")}
          value={statusText}
          meta={checkedAt}
          icon={<Activity className="h-3.5 w-3.5" />}
          tone={apiTone}
          loading={isLoading}
        />
        <KpiCard
          label={t("dashboard.kpis.database")}
          value={dbText}
          meta="PostgreSQL / Django ORM"
          icon={<Database className="h-3.5 w-3.5" />}
          tone={dbTone}
          loading={isLoading}
        />
        <KpiCard
          label={t("dashboard.kpis.redis")}
          value={redisText}
          meta="Cache & Celery Broker"
          icon={<Server className="h-3.5 w-3.5" />}
          tone={redisTone}
          loading={isLoading}
        />
        <KpiCard
          label={t("dashboard.kpis.apiVersion")}
          value={data ? `v${toLocaleDigits(data.version, lang)}` : "—"}
          meta="OpenAPI 3.0"
          icon={<ShieldCheck className="h-3.5 w-3.5" />}
          tone={data ? "neutral" : "danger"}
          loading={isLoading}
        />
      </section>

      <section className="rounded-lg border border-border bg-surface p-4 shadow-[0_1px_2px_rgba(17,24,39,0.03)]">
        <div className="mb-3 flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">{t("dashboard.modules.heading")}</h2>
          <span className="text-[11px] text-ink-subtle">{t("dashboard.modules.subheading")}</span>
        </div>

        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {MODULE_LINKS.map((mod) => (
            <Link
              key={mod.to}
              to={mod.to}
              className="group flex items-start gap-3 rounded-md border border-border bg-canvas/50 p-3 transition-colors hover:border-primary/40 hover:bg-primary-soft/30"
            >
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border bg-surface">
                {mod.icon}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-ink group-hover:text-primary">
                  {t(mod.titleKey)}
                </p>
                <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">{t(mod.descKey)}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
