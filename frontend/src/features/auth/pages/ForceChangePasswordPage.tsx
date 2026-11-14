import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/errors";
import { authApi } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/store/authStore";
import {
  changePasswordSchema,
  type ChangePasswordFormData,
} from "@/features/auth/schemas/authSchemas";

export function ForceChangePasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const updateUserPreferences = useAuthStore((s) => s.updateUserPreferences);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const form = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      old_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const onSubmit = async (data: ChangePasswordFormData) => {
    setGeneralError(null);
    try {
      await authApi.changePassword({
        old_password: data.old_password,
        new_password: data.new_password,
      });

      updateUserPreferences({ must_change_password: false });
      void navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setGeneralError(err.message || t("auth.passwordChangeFailed", "Failed to change password."));
      } else {
        setGeneralError(t("auth.passwordChangeFailed", "Failed to change password."));
      }
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-8 text-ink">
      <Card className="w-full max-w-sm animate-page-enter">
        <CardHeader>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-warning/10 text-warning mb-2">
            <Lock className="h-5 w-5" />
          </div>
          <CardTitle>{t("auth.forceChangePasswordTitle", "Change Temporary Password")}</CardTitle>
          <p className="mt-0.5 text-xs text-ink-muted">
            {t("auth.forceChangePasswordSubtitle", "For your security, please update your temporary password before accessing the system.")}
          </p>
        </CardHeader>
        <CardContent>
          {generalError && (
            <div className="mb-3 flex items-start gap-2 rounded-md bg-danger/10 p-2.5 text-xs text-danger" role="alert">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{generalError}</span>
            </div>
          )}

          <form onSubmit={(e) => void form.handleSubmit(onSubmit)(e)} className="space-y-3">
            <FormField>
              <FormLabel htmlFor="old_password" required>
                {t("auth.currentPassword", "Current Temporary Password")}
              </FormLabel>
              <Input
                id="old_password"
                type="password"
                placeholder="••••••••"
                disabled={form.formState.isSubmitting}
                {...form.register("old_password")}
              />
              {form.formState.errors.old_password && (
                <p className="mt-1 text-xs text-danger">{t(form.formState.errors.old_password.message ?? "")}</p>
              )}
            </FormField>

            <FormField>
              <FormLabel htmlFor="new_password" required>
                {t("auth.newPassword", "New Password")}
              </FormLabel>
              <Input
                id="new_password"
                type="password"
                placeholder="••••••••"
                disabled={form.formState.isSubmitting}
                {...form.register("new_password")}
              />
              {form.formState.errors.new_password && (
                <p className="mt-1 text-xs text-danger">{t(form.formState.errors.new_password.message ?? "")}</p>
              )}
            </FormField>

            <FormField>
              <FormLabel htmlFor="confirm_password" required>
                {t("auth.confirmPassword", "Confirm New Password")}
              </FormLabel>
              <Input
                id="confirm_password"
                type="password"
                placeholder="••••••••"
                disabled={form.formState.isSubmitting}
                {...form.register("confirm_password")}
              />
              {form.formState.errors.confirm_password && (
                <p className="mt-1 text-xs text-danger">{t(form.formState.errors.confirm_password.message ?? "")}</p>
              )}
            </FormField>

            <div className="rounded-md bg-canvas p-2.5 text-[11px] text-ink-muted">
              <p className="font-semibold text-ink">{t("auth.passwordRequirementsTitle", "Requirements:")}</p>
              <ul className="mt-1 list-disc pl-4 space-y-0.5">
                <li>{t("auth.requirementLength", "At least 8 characters long")}</li>
                <li>{t("auth.requirementUppercase", "At least 1 uppercase letter")}</li>
                <li>{t("auth.requirementNumber", "At least 1 digit")}</li>
              </ul>
            </div>

            <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? t("common.loading", "Updating...") : t("auth.updatePasswordButton", "Update Password & Continue")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
