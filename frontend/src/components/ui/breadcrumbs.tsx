import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-[11px] text-ink-subtle">
      {items.map((item, idx) => (
        <span key={item.label} className="inline-flex items-center gap-1">
          {idx > 0 ? <ChevronRight className="h-3 w-3 shrink-0" aria-hidden="true" /> : null}
          {item.to && idx < items.length - 1 ? (
            <Link to={item.to} className="hover:text-ink hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className={idx === items.length - 1 ? "font-medium text-ink" : undefined}>
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
