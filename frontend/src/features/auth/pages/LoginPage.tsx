import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Lock, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { setAppLanguage, type SupportedLanguage } from "@/i18n";
import { cn } from "@/lib/utils";

interface LoginPageProps {
  onLoginSuccess: () => void;
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { t, i18n } = useTranslation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const currentLang: SupportedLanguage = i18n.language === "bn" ? "bn" : "en";

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password.trim()) {
      return;
    }
    onLoginSuccess();
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-8 text-ink">
      <div className="mb-4 flex w-full max-w-sm items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-sm font-bold text-white">
            বি
          </span>
          <div>
            <p className="text-sm font-semibold leading-tight text-ink">{t("app.brandName")}</p>
            <p className="text-[11px] leading-tight text-ink-subtle">{t("app.brandTag")}</p>
          </div>
        </div>

        <div
          className="inline-flex items-center rounded-md border border-border bg-surface p-0.5"
          role="group"
          aria-label={t("app.language.label")}
        >
          <button
            type="button"
            onClick={() => setAppLanguage("en")}
            aria-pressed={currentLang === "en"}
            aria-label={t("app.language.switchToEnglish")}
            className={cn(
              "rounded px-2 py-1 text-[11px] font-semibold transition-colors",
              currentLang === "en" ? "bg-primary text-white" : "text-ink-muted hover:text-ink",
            )}
          >
            {t("app.language.en")}
          </button>
          <button
            type="button"
            onClick={() => setAppLanguage("bn")}
            aria-pressed={currentLang === "bn"}
            aria-label={t("app.language.switchToBangla")}
            className={cn(
              "rounded px-2 py-1 text-[11px] font-semibold transition-colors",
              currentLang === "bn" ? "bg-primary text-white" : "text-ink-muted hover:text-ink",
            )}
          >
            {t("app.language.bn")}
          </button>
        </div>
      </div>

      <Card className="w-full max-w-sm animate-page-enter">
        <CardHeader>
          <CardTitle>{t("auth.signInTitle")}</CardTitle>
          <p className="mt-0.5 text-xs text-ink-muted">{t("auth.signInSubtitle")}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-3">
            <FormField>
              <FormLabel htmlFor="login-identifier" required>
                {t("auth.identifierLabel")}
              </FormLabel>
              <div className="relative">
                <Phone
                  className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle"
                  aria-hidden="true"
                />
                <Input
                  id="login-identifier"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="+8801XXXXXXXXX"
                  className="pl-8"
                  required
                />
              </div>
            </FormField>

            <FormField>
              <FormLabel htmlFor="login-password" required>
                {t("auth.passwordLabel")}
              </FormLabel>
              <div className="relative">
                <Lock
                  className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle"
                  aria-hidden="true"
                />
                <Input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-8"
                  required
                />
              </div>
            </FormField>

            <Button type="submit" className="w-full">
              {t("auth.signInAction")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
