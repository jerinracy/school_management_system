import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-canvas/50 px-4 py-8 text-center">
      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-ink-subtle">
        {icon ?? <Inbox className="h-4 w-4" aria-hidden="true" />}
      </span>
      <p className="mt-2.5 text-xs font-semibold text-ink">{title}</p>
      {description ? <p className="mt-1 max-w-sm text-[11px] text-ink-muted">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}
