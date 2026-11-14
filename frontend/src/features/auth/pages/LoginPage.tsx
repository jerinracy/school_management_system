import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Lock, Phone, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { setAppLanguage, type SupportedLanguage } from "@/i18n";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/errors";
import { authApi } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/store/authStore";
import {
  loginSchema,
  otpRequestSchema,
  otpVerifySchema,
  type LoginFormData,
  type OtpRequestFormData,
  type OtpVerifyFormData,
} from "@/features/auth/schemas/authSchemas";

interface LoginPageProps {
  onLoginSuccess?: () => void;
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);

  const [activeTab, setActiveTab] = useState<"password" | "otp">("password");
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [totpPrompt, setTotpPrompt] = useState<string | null>(null);

  // OTP flow state
  const [otpSent, setOtpSent] = useState(false);
  const [otpPhone, setOtpPhone] = useState("");

  const currentLang: SupportedLanguage = i18n.language === "bn" ? "bn" : "en";

  // Password Form
  const passwordForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: "", password: "" },
  });

  // OTP Request Form
  const otpReqForm = useForm<OtpRequestFormData>({
    resolver: zodResolver(otpRequestSchema),
    defaultValues: { phone: "" },
  });

  // OTP Verify Form
  const otpVerifyForm = useForm<OtpVerifyFormData>({
    resolver: zodResolver(otpVerifySchema),
    defaultValues: { phone: "", code: "" },
  });

  const handlePasswordSubmit = async (data: LoginFormData) => {
    setGeneralError(null);
    setTotpPrompt(null);
    try {
      const response = await authApi.login({
        identifier: data.identifier,
        password: data.password,
        platform: "web",
      });

      // Handle 2FA prompt
      if ("code" in response && response.code === "TOTP_REQUIRED") {
        setTotpPrompt(t("auth.totpRequiredNotice", "Two-factor authentication is required for this account. Note: Backend 2FA verify endpoint is currently in development."));
        return;
      }

      if ("access" in response && "refresh" in response && response.user) {
        setTokens(response.access, response.refresh);
        setUser(response.user);
        onLoginSuccess?.();
        if (response.user.must_change_password) {
          void navigate("/force-change-password");
        } else {
          void navigate("/");
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "ACCOUNT_LOCKED" || err.status === 429) {
          setGeneralError(t("auth.accountLocked", "Account locked due to multiple failed attempts. Try again in 15 minutes."));
        } else if (err.status === 401) {
          setGeneralError(t("auth.invalidCredentials", "Invalid username/phone or password."));
        } else {
          setGeneralError(err.message || t("auth.loginFailed", "Login failed."));
        }
      } else {
        setGeneralError(t("auth.loginFailed", "Login failed. Please check your network connection."));
      }
    }
  };

  const handleOtpRequest = async (data: OtpRequestFormData) => {
    setGeneralError(null);
    try {
      await authApi.requestOtp({
        phone: data.phone,
        purpose: "login",
      });
      setOtpPhone(data.phone);
      setOtpSent(true);
      otpVerifyForm.setValue("phone", data.phone);
    } catch (err) {
      if (err instanceof ApiError) {
        setGeneralError(err.message || t("auth.otpRequestFailed", "Failed to send OTP."));
      } else {
        setGeneralError(t("auth.otpRequestFailed", "Failed to send OTP."));
      }
    }
  };

  const handleOtpVerify = async (data: OtpVerifyFormData) => {
    setGeneralError(null);
    try {
      const response = await authApi.verifyOtp({
        phone: data.phone,
        code: data.code,
        purpose: "login",
        platform: "web",
      });

      if (response && response.access && response.refresh && response.user) {
        setTokens(response.access, response.refresh);
        setUser(response.user);
        onLoginSuccess?.();
        if (response.user.must_change_password) {
          void navigate("/force-change-password");
        } else {
          void navigate("/");
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setGeneralError(err.message || t("auth.invalidOtp", "Invalid or expired OTP code."));
      } else {
        setGeneralError(t("auth.invalidOtp", "Invalid or expired OTP code."));
      }
    }
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
          {generalError && (
            <div className="mb-3 flex items-start gap-2 rounded-md bg-danger/10 p-2.5 text-xs text-danger" role="alert">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{generalError}</span>
            </div>
          )}

          {totpPrompt && (
            <div className="mb-3 flex items-start gap-2 rounded-md bg-warning/10 p-2.5 text-xs text-warning" role="alert">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{totpPrompt}</span>
            </div>
          )}

          <Tabs value={activeTab} onValueChange={(val) => { setActiveTab(val as "password" | "otp"); setGeneralError(null); }} className="w-full">
            <TabsList className="mb-4 grid w-full grid-cols-2">
              <TabsTrigger value="password">{t("auth.passwordTab", "Password")}</TabsTrigger>
              <TabsTrigger value="otp">{t("auth.otpTab", "Phone OTP")}</TabsTrigger>
            </TabsList>

            <TabsContent value="password">
              <form onSubmit={(e) => void passwordForm.handleSubmit(handlePasswordSubmit)(e)} className="space-y-3">
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
                      placeholder="+8801XXXXXXXXX"
                      className="pl-8"
                      disabled={passwordForm.formState.isSubmitting}
                      {...passwordForm.register("identifier")}
                    />
                  </div>
                  {passwordForm.formState.errors.identifier && (
                    <p className="mt-1 text-xs text-danger">{t(passwordForm.formState.errors.identifier.message ?? "validation.identifierRequired")}</p>
                  )}
                </FormField>

                <FormField>
                  <div className="flex items-center justify-between">
                    <FormLabel htmlFor="login-password" required>
                      {t("auth.passwordLabel")}
                    </FormLabel>
                    <Link to="/forgot-password" className="text-[11px] text-primary hover:underline">
                      {t("auth.forgotPasswordLink", "Forgot password?")}
                    </Link>
                  </div>
                  <div className="relative">
                    <Lock
                      className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle"
                      aria-hidden="true"
                    />
                    <Input
                      id="login-password"
                      type="password"
                      placeholder="••••••••"
                      className="pl-8"
                      disabled={passwordForm.formState.isSubmitting}
                      {...passwordForm.register("password")}
                    />
                  </div>
                  {passwordForm.formState.errors.password && (
                    <p className="mt-1 text-xs text-danger">{t(passwordForm.formState.errors.password.message ?? "validation.passwordRequired")}</p>
                  )}
                </FormField>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={passwordForm.formState.isSubmitting}
                >
                  {passwordForm.formState.isSubmitting ? t("common.loading", "Signing in...") : t("auth.signInButton")}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="otp">
              {!otpSent ? (
                <form onSubmit={(e) => void otpReqForm.handleSubmit(handleOtpRequest)(e)} className="space-y-3">
                  <FormField>
                    <FormLabel htmlFor="otp-phone" required>
                      {t("auth.phoneLabel", "Mobile Number")}
                    </FormLabel>
                    <div className="relative">
                      <Phone className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle" />
                      <Input
                        id="otp-phone"
                        placeholder="+8801XXXXXXXXX"
                        className="pl-8"
                        disabled={otpReqForm.formState.isSubmitting}
                        {...otpReqForm.register("phone")}
                      />
                    </div>
                    {otpReqForm.formState.errors.phone && (
                      <p className="mt-1 text-xs text-danger">{t(otpReqForm.formState.errors.phone.message ?? "validation.phoneInvalid")}</p>
                    )}
                  </FormField>

                  <Button type="submit" className="w-full" disabled={otpReqForm.formState.isSubmitting}>
                    {otpReqForm.formState.isSubmitting ? t("common.loading", "Sending OTP...") : t("auth.sendOtpButton", "Send OTP Code")}
                  </Button>
                </form>
              ) : (
                <form onSubmit={(e) => void otpVerifyForm.handleSubmit(handleOtpVerify)(e)} className="space-y-3">
                  <div className="rounded-md bg-canvas p-2 text-xs text-ink-muted">
                    <p>{t("auth.otpSentTo", "6-digit OTP code sent to:")} <span className="font-semibold text-ink">{otpPhone}</span></p>
                    <button
                      type="button"
                      onClick={() => { setOtpSent(false); setGeneralError(null); }}
                      className="mt-1 text-[11px] text-primary hover:underline"
                    >
                      {t("auth.changePhone", "Change number")}
                    </button>
                  </div>

                  <FormField>
                    <FormLabel htmlFor="otp-code" required>
                      {t("auth.otpCodeLabel", "Enter 6-digit Code")}
                    </FormLabel>
                    <Input
                      id="otp-code"
                      placeholder="123456"
                      maxLength={6}
                      className="text-center font-mono text-base tracking-widest"
                      disabled={otpVerifyForm.formState.isSubmitting}
                      {...otpVerifyForm.register("code")}
                    />
                    {otpVerifyForm.formState.errors.code && (
                      <p className="mt-1 text-xs text-danger">{t(otpVerifyForm.formState.errors.code.message ?? "validation.otpCodeLength")}</p>
                    )}
                  </FormField>

                  <Button type="submit" className="w-full" disabled={otpVerifyForm.formState.isSubmitting}>
                    {otpVerifyForm.formState.isSubmitting ? t("common.loading", "Verifying...") : t("auth.verifyOtpButton", "Verify & Sign In")}
                  </Button>
                </form>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
