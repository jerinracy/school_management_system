import { AlertCircle, CheckCircle2, Clock, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_STYLES: Record<StatusTone, string> = {
  success: "border-primary-border bg-primary-soft text-primary",
  warning: "border-amber-200 bg-academic-amberSoft text-academic-amber dark:border-amber-800",
  danger: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300",
  info: "border-blue-200 bg-academic-navySoft text-academic-navy dark:border-blue-900",
  neutral: "border-border bg-canvas text-ink-muted",
};

const TONE_ICONS: Record<StatusTone, ReactNode> = {
  success: <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />,
  warning: <Clock className="h-3 w-3 shrink-0" aria-hidden="true" />,
  danger: <XCircle className="h-3 w-3 shrink-0" aria-hidden="true" />,
  info: <Info className="h-3 w-3 shrink-0" aria-hidden="true" />,
  neutral: <AlertCircle className="h-3 w-3 shrink-0" aria-hidden="true" />,
};

interface StatusChipProps {
  label: string;
  tone?: StatusTone;
  icon?: ReactNode;
  className?: string;
}

export function StatusChip({ label, tone = "neutral", icon, className }: StatusChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium leading-tight",
        TONE_STYLES[tone],
        className,
      )}
    >
      {icon ?? TONE_ICONS[tone]}
      <span>{label}</span>
    </span>
  );
}
