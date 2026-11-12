import { Printer } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

interface PrintLayoutProps {
  title: string;
  children: ReactNode;
}

export function PrintLayout({ title, children }: PrintLayoutProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3">
      <div className="no-print flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-2.5">
        <span className="text-xs font-medium text-ink">{title}</span>
        <Button variant="secondary" size="sm" onClick={() => window.print()}>
          <Printer className="h-3.5 w-3.5" />
          <span>{t("ui.print.action")}</span>
        </Button>
      </div>
      <div className="mx-auto max-w-[210mm] rounded-lg border border-border bg-white p-6 text-slate-900 shadow-sm print:border-0 print:p-0 print:shadow-none">
        {children}
      </div>
    </div>
  );
}
