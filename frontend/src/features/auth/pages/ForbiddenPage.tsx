import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";

export function ForbiddenPage() {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger/10 text-danger">
        <ShieldAlert className="h-6 w-6" />
      </div>
      <h1 className="mt-4 text-xl font-bold text-ink">{t("auth.forbiddenTitle", "Access Denied")}</h1>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        {t("auth.forbiddenSubtitle", "You do not have permission to view this resource. Contact your administrator if you believe this is an error.")}
      </p>
      <div className="mt-6">
        <Link to="/" className={buttonVariants({ variant: "outline" })}>
          {t("auth.backToHome", "Back to Dashboard")}
        </Link>
      </div>
    </div>
  );
}
