import { AlertTriangle, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

interface ErrorPageProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorPage({ title, message, onRetry }: ErrorPageProps) {
  const { t } = useTranslation();

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-lg border border-rose-200 bg-rose-50/70 px-6 py-10 text-center dark:border-rose-900 dark:bg-rose-950/40"
    >
      <AlertTriangle className="h-6 w-6 text-rose-600" aria-hidden="true" />
      <h2 className="mt-2.5 text-sm font-semibold text-ink">
        {title ?? t("ui.errorPage.title")}
      </h2>
      <p className="mt-1 max-w-md text-xs text-ink-muted">
        {message ?? t("ui.errorPage.description")}
      </p>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-4">
          <RefreshCw className="h-3.5 w-3.5" />
          <span>{t("ui.errorPage.retry")}</span>
        </Button>
      ) : null}
    </div>
  );
}
