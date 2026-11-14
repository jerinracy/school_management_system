import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, ArrowLeft, CheckCircle2, Info, Phone } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/errors";
import { authApi } from "@/features/auth/api/authApi";
import {
  otpRequestSchema,
  type OtpRequestFormData,
} from "@/features/auth/schemas/authSchemas";

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submittedPhone, setSubmittedPhone] = useState<string | null>(null);

  const form = useForm<OtpRequestFormData>({
    resolver: zodResolver(otpRequestSchema),
    defaultValues: { phone: "" },
  });

  const onSubmit = async (data: OtpRequestFormData) => {
    setGeneralError(null);
    try {
      await authApi.requestOtp({
        phone: data.phone,
        purpose: "password_reset",
      });
      setSubmittedPhone(data.phone);
    } catch (err) {
      if (err instanceof ApiError) {
        setGeneralError(err.message || t("auth.otpRequestFailed", "Failed to send reset code."));
      } else {
        setGeneralError(t("auth.otpRequestFailed", "Failed to send reset code."));
      }
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-8 text-ink">
      <Card className="w-full max-w-sm animate-page-enter">
        <CardHeader>
          <CardTitle>{t("auth.forgotPasswordTitle", "Reset Password")}</CardTitle>
          <p className="mt-0.5 text-xs text-ink-muted">
            {t("auth.forgotPasswordSubtitle", "Enter your registered mobile number to receive a verification code.")}
          </p>
        </CardHeader>
        <CardContent>
          {generalError && (
            <div className="mb-3 flex items-start gap-2 rounded-md bg-danger/10 p-2.5 text-xs text-danger" role="alert">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{generalError}</span>
            </div>
          )}

          {!submittedPhone ? (
            <form onSubmit={(e) => void form.handleSubmit(onSubmit)(e)} className="space-y-3">
              <FormField>
                <FormLabel htmlFor="reset-phone" required>
                  {t("auth.phoneLabel", "Mobile Number")}
                </FormLabel>
                <div className="relative">
                  <Phone className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle" />
                  <Input
                    id="reset-phone"
                    placeholder="+8801XXXXXXXXX"
                    className="pl-8"
                    disabled={form.formState.isSubmitting}
                    {...form.register("phone")}
                  />
                </div>
                {form.formState.errors.phone && (
                  <p className="mt-1 text-xs text-danger">{t(form.formState.errors.phone.message ?? "")}</p>
                )}
              </FormField>

              <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? t("common.loading", "Sending...") : t("auth.sendResetCodeButton", "Send Reset Code")}
              </Button>

              <div className="pt-2 text-center">
                <Link to="/login" className="inline-flex items-center gap-1 text-xs text-ink-muted hover:text-ink">
                  <ArrowLeft className="h-3 w-3" />
                  {t("auth.backToSignIn", "Back to Sign In")}
                </Link>
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start gap-2 rounded-md bg-success/10 p-2.5 text-xs text-success">
                <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  {t("auth.resetCodeSentNotice", "If an account exists with this number, a verification OTP has been dispatched.")}
                </span>
              </div>

              <div className="flex items-start gap-2 rounded-md bg-canvas p-2.5 text-xs text-ink-muted">
                <Info className="h-4 w-4 shrink-0 text-primary mt-0.5" />
                <span>
                  {t("auth.resetPasswordBackendNotice", "Contact your school administrator or teacher to complete password reset confirmation.")}
                </span>
              </div>

              <Link to="/login" className={buttonVariants({ variant: "outline", className: "w-full justify-center" })}>
                {t("auth.backToSignIn", "Back to Sign In")}
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
