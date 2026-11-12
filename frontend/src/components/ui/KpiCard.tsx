import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type KpiTone = "neutral" | "success" | "warning" | "danger";

interface KpiCardProps {
  label: string;
  value: string;
  meta?: string;
  icon: ReactNode;
  tone?: KpiTone;
  loading?: boolean;
}

const TONE_DOT: Record<KpiTone, string> = {
  neutral: "bg-slate-400",
  success: "bg-emerald-600",
  warning: "bg-amber-600",
  danger: "bg-rose-600",
};

const TONE_ICON_BG: Record<KpiTone, string> = {
  neutral: "bg-slate-100 text-slate-700",
  success: "bg-primary-soft text-primary",
  warning: "bg-academic-amberSoft text-academic-amber",
  danger: "bg-rose-50 text-rose-700",
};

export function KpiCard({
  label,
  value,
  meta,
  icon,
  tone = "neutral",
  loading = false,
}: KpiCardProps) {
  if (loading) {
    return (
      <div
        className="rounded-lg border border-border bg-surface px-3.5 py-3 shadow-[0_1px_2px_rgba(17,24,39,0.03)]"
        aria-busy="true"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="h-3 w-20 animate-pulse rounded bg-slate-200" />
          <div className="h-6 w-6 animate-pulse rounded bg-slate-100" />
        </div>
        <div className="mt-2 h-5 w-24 animate-pulse rounded bg-slate-200" />
        <div className="mt-1.5 h-3 w-16 animate-pulse rounded bg-slate-100" />
      </div>
    );
  }

  return (
    <article className="animate-data-fade rounded-lg border border-border bg-surface px-3.5 py-3 shadow-[0_1px_2px_rgba(17,24,39,0.03)] transition-colors hover:border-border-strong">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-ink-subtle">
          {label}
        </span>
        <span
          className={cn(
            "inline-flex h-6 w-6 items-center justify-center rounded",
            TONE_ICON_BG[tone],
          )}
          aria-hidden="true"
        >
          {icon}
        </span>
      </div>
      <div className="mt-1.5 flex items-center gap-2">
        <span className={cn("h-2 w-2 shrink-0 rounded-full", TONE_DOT[tone])} aria-hidden="true" />
        <p className="tabular-nums truncate text-base font-semibold leading-tight text-ink">
          {value}
        </p>
      </div>
      {meta ? (
        <p className="tabular-nums mt-1 truncate text-[11px] text-ink-muted">{meta}</p>
      ) : null}
    </article>
  );
}
