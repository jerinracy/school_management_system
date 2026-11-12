import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowLeft, Layers } from "lucide-react";

interface ModulePlaceholderPageProps {
  titleKey: string;
}

export function ModulePlaceholderPage({ titleKey }: ModulePlaceholderPageProps) {
  const { t } = useTranslation();

  return (
    <div className="rounded-lg border border-border bg-surface p-5 shadow-[0_1px_2px_rgba(17,24,39,0.03)]">
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-soft text-primary">
          <Layers className="h-4 w-4" />
        </span>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wider text-ink-subtle">
            {t("placeholder.routeLabel")}
          </p>
          <h1 className="text-base font-semibold text-ink">{t(titleKey)}</h1>
        </div>
      </div>

      <p className="mt-3 text-xs text-ink-muted">{t("placeholder.underConstruction")}</p>

      <div className="mt-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-canvas px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-slate-100"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{t("placeholder.backToOverview")}</span>
        </Link>
      </div>
    </div>
  );
}
