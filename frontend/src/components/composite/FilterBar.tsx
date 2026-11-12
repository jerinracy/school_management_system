import { Search, X } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface FilterBarProps {
  searchParamKey?: string;
  searchPlaceholder?: string;
  children?: ReactNode;
  onReset?: () => void;
}

export function FilterBar({
  searchParamKey = "q",
  searchPlaceholder,
  children,
  onReset,
}: FilterBarProps) {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get(searchParamKey) ?? "";

  const updateQuery = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(searchParamKey, value);
    } else {
      next.delete(searchParamKey);
    }
    next.set("page", "1");
    setSearchParams(next, { replace: true });
  };

  const handleReset = () => {
    const next = new URLSearchParams(searchParams);
    next.delete(searchParamKey);
    next.set("page", "1");
    setSearchParams(next, { replace: true });
    onReset?.();
  };

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-2.5 shadow-[0_1px_2px_rgba(17,24,39,0.02)]">
      <div className="relative min-w-[14rem] flex-1">
        <Search
          className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle"
          aria-hidden="true"
        />
        <Input
          value={query}
          onChange={(e) => updateQuery(e.target.value)}
          placeholder={searchPlaceholder ?? t("ui.filterBar.searchPlaceholder")}
          aria-label={searchPlaceholder ?? t("ui.filterBar.searchPlaceholder")}
          className="pl-8"
        />
      </div>
      {children}
      {query ? (
        <Button variant="ghost" size="sm" onClick={handleReset}>
          <X className="h-3.5 w-3.5" />
          <span>{t("ui.filterBar.clear")}</span>
        </Button>
      ) : null}
    </div>
  );
}
