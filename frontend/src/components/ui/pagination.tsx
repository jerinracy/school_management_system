import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toLocaleDigits } from "@/lib/format";
import { Button } from "./button";

interface PaginationProps {
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (nextPage: number) => void;
}

export function Pagination({ page, pageSize, totalCount, onPageChange }: PaginationProps) {
  const { t, i18n } = useTranslation();
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const start = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(totalCount, page * pageSize);

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-3 py-2 text-xs text-ink-muted">
      <span className="tabular-nums text-[11px]">
        {t("ui.pagination.showing", {
          start: toLocaleDigits(start, i18n.language),
          end: toLocaleDigits(end, i18n.language),
          total: toLocaleDigits(totalCount, i18n.language),
        })}
      </span>
      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label={t("ui.pagination.prev")}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          <span>{t("ui.pagination.prev")}</span>
        </Button>
        <span className="tabular-nums px-1.5 text-[11px] font-medium text-ink">
          {toLocaleDigits(page, i18n.language)} / {toLocaleDigits(totalPages, i18n.language)}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          aria-label={t("ui.pagination.next")}
        >
          <span>{t("ui.pagination.next")}</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
