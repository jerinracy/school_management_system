import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  Lock,
  Moon,
  Phone,
  ShieldAlert,
  ShieldCheck,
  Sun,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { setAppLanguage, type SupportedLanguage } from "@/i18n";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/theme";
import { ApiError } from "@/lib/errors";
import { authApi } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";
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
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);

  const { branding, fetchBranding, getLocalizedName, getLogoUrl } = useBrandingStore();

  const [activeTab, setActiveTab] = useState<"password" | "otp">("password");
  const [showPassword, setShowPassword] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [totpPrompt, setTotpPrompt] = useState<string | null>(null);

  // OTP flow state
  const [otpSent, setOtpSent] = useState(false);
  const [otpPhone, setOtpPhone] = useState("");

  const currentLang: SupportedLanguage = i18n.language === "bn" ? "bn" : "en";
  const schoolName = getLocalizedName(currentLang);
  const schoolLogo = getLogoUrl();
  const schoolEIIN = branding?.eiin;
  const schoolBoard = branding?.board;

  useEffect(() => {
    void fetchBranding();
  }, [fetchBranding]);

  // Update document title dynamically
  useEffect(() => {
    document.title = `${schoolName} — ${t("auth.signInTitle")}`;
  }, [schoolName, t]);

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
        setTotpPrompt(
          t(
            "auth.totpRequiredNotice",
            "Two-factor authentication is required for this account.",
          ),
        );
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
          setGeneralError(
            t(
              "auth.accountLocked",
              "Account locked due to multiple failed attempts. Try again in 15 minutes.",
            ),
          );
        } else if (err.status === 401) {
          setGeneralError(
            t("auth.invalidCredentials", "Invalid username/phone or password."),
          );
        } else {
          setGeneralError(err.message || t("auth.loginFailed", "Login failed."));
        }
      } else {
        setGeneralError(
          t("auth.loginFailed", "Login failed. Please check your network connection."),
        );
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
    <div className="flex min-h-screen w-full flex-col lg:flex-row bg-[#F8F9FA] dark:bg-canvas text-ink">
      {/* ========================================================================= */}
      {/* LEFT PANEL: Dignified Institutional Identity (Light, Clean, Elegant)      */}
      {/* ========================================================================= */}
      <div className="relative hidden w-full lg:flex lg:w-[48%] xl:w-[50%] flex-col justify-between overflow-hidden border-r border-border/70 bg-white/70 dark:bg-surface/40 p-12 xl:p-16 backdrop-blur-md">
        {/* Subtle, airy ambient light decorative motif */}
        <div
          className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-primary/[0.04] blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-24 -right-24 h-96 w-96 rounded-full bg-emerald-500/[0.03] blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03] bg-[radial-gradient(#0F5C46_1px,transparent_1px)] [background-size:24px_24px]"
          aria-hidden="true"
        />

        {/* Top: Institutional Recognition Badge */}
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary-soft/60 px-3.5 py-1 text-xs font-semibold text-primary">
            <GraduationCap className="h-4 w-4" />
            <span>{t("auth.officialPortal", "Government EIIN Compliant Official Portal")}</span>
          </div>
        </div>

        {/* Center: School Brand Presentation (Logo + School Name + Accreditations) */}
        <div className="relative z-10 my-auto py-8">
          <div className="flex flex-col items-start space-y-6">
            {/* School Crest / Logo Frame */}
            {schoolLogo ? (
              <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl border border-border/80 bg-white dark:bg-surface p-3 shadow-xs">
                <img
                  src={schoolLogo}
                  alt={schoolName}
                  className="h-full w-full object-contain"
                />
              </div>
            ) : (
              <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl border border-primary/20 bg-primary-soft text-3xl font-extrabold text-primary shadow-xs">
                {currentLang === "bn" ? "বি" : schoolName.charAt(0).toUpperCase() || "S"}
              </div>
            )}

            {/* School Title & Affiliations */}
            <div className="space-y-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-ink xl:text-4xl leading-tight">
                {schoolName}
              </h1>

              {/* Official Badges */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {schoolEIIN && (
                  <span className="inline-flex items-center rounded-md border border-border bg-white dark:bg-surface px-2.5 py-1 text-xs font-semibold text-ink-muted shadow-2xs">
                    {t("auth.eiinLabel", "EIIN")}: {schoolEIIN}
                  </span>
                )}
                {schoolBoard && (
                  <span className="inline-flex items-center rounded-md border border-border bg-white dark:bg-surface px-2.5 py-1 text-xs font-medium text-ink-subtle capitalize shadow-2xs">
                    {schoolBoard} {t("auth.boardLabel", "Board")}
                  </span>
                )}
                <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/20 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Authorized Portal</span>
                </span>
              </div>

              {/* Dignified Institutional Subtitle */}
              <p className="max-w-md pt-2 text-sm text-ink-muted leading-relaxed">
                Academic Administration, Student Information & Smart Campus Management System.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom: Institutional Compliance Note */}
        <div className="relative z-10 flex items-center justify-between border-t border-border/70 pt-6 text-xs text-ink-subtle">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>Ministry of Education Curriculum Compliant</span>
          </div>
          <span>&copy; {new Date().getFullYear()} {schoolName}</span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* RIGHT PANEL: Clean, Focused Authentication Workspace                      */}
      {/* ========================================================================= */}
      <div className="flex w-full flex-1 flex-col justify-between p-6 sm:p-10 lg:w-[52%] xl:w-[50%] xl:p-14">
        {/* Top Header: Mobile Identity + Language & Theme Toggles */}
        <div className="flex items-center justify-between pb-4">
          {/* Mobile-only Branding */}
          <div className="flex items-center gap-2.5 lg:hidden">
            {schoolLogo ? (
              <img
                src={schoolLogo}
                alt={schoolName}
                className="h-9 w-9 object-contain rounded-lg border border-border bg-white p-1"
              />
            ) : (
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-soft text-xs font-bold text-primary">
                {currentLang === "bn" ? "বি" : schoolName.charAt(0).toUpperCase() || "S"}
              </span>
            )}
            <div className="min-w-0">
              <p className="truncate text-xs font-bold text-ink leading-tight">
                {schoolName}
              </p>
              {schoolEIIN && (
                <p className="text-[10px] text-ink-subtle">
                  {t("auth.eiinLabel", "EIIN")}: {schoolEIIN}
                </p>
              )}
            </div>
          </div>

          <div className="hidden lg:flex items-center gap-2 text-xs font-medium text-ink-subtle">
            <Building2 className="h-3.5 w-3.5 text-primary" />
            <span>{schoolName}</span>
          </div>

          {/* Right Utility Actions */}
          <div className="flex items-center gap-2 ml-auto">
            {/* Language Switcher */}
            <div
              className="inline-flex items-center rounded-lg border border-border bg-white dark:bg-surface p-0.5 shadow-2xs"
              role="group"
              aria-label={t("app.language.label")}
            >
              <button
                type="button"
                onClick={() => setAppLanguage("en")}
                aria-pressed={currentLang === "en"}
                aria-label={t("app.language.switchToEnglish")}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-semibold transition-colors",
                  currentLang === "en"
                    ? "bg-primary text-white shadow-2xs"
                    : "text-ink-muted hover:text-ink",
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
                  "rounded-md px-2.5 py-1 text-xs font-semibold transition-colors",
                  currentLang === "bn"
                    ? "bg-primary text-white shadow-2xs"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {t("app.language.bn")}
              </button>
            </div>

            {/* Dark / Light Mode Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === "light" ? t("topbar.darkMode") : t("topbar.lightMode")}
              className="rounded-lg border border-border bg-white dark:bg-surface p-1.5 text-ink-muted transition-colors hover:text-ink shadow-2xs"
            >
              {theme === "light" ? (
                <Moon className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Sun className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Center: Clean Elevated Authentication Card */}
        <div className="mx-auto my-auto w-full max-w-md py-6">
          <div className="rounded-2xl border border-border/80 bg-white dark:bg-surface p-7 sm:p-9 shadow-xs">
            {/* Card Header */}
            <div className="mb-6 space-y-1">
              <h2 className="text-2xl font-bold tracking-tight text-ink">
                {t("auth.signInTitle", "Admin Sign In")}
              </h2>
              <p className="text-xs text-ink-muted sm:text-sm">
                {t("auth.signInSubtitle", "Access your institution academic and administrative workspace.")}
              </p>
            </div>

            {generalError && (
              <div
                className="mb-5 flex items-start gap-2.5 rounded-lg border border-danger/20 bg-danger/10 p-3 text-xs text-danger animate-fade-in"
                role="alert"
              >
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span className="font-medium">{generalError}</span>
              </div>
            )}

            {totpPrompt && (
              <div
                className="mb-5 flex items-start gap-2.5 rounded-lg border border-warning/20 bg-warning/10 p-3 text-xs text-warning animate-fade-in"
                role="alert"
              >
                <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                <span className="font-medium">{totpPrompt}</span>
              </div>
            )}

            {/* Segmented Auth Method Tabs */}
            <Tabs
              value={activeTab}
              onValueChange={(val) => {
                setActiveTab(val as "password" | "otp");
                setGeneralError(null);
              }}
              className="w-full"
            >
              <TabsList className="mb-5 grid w-full grid-cols-2 rounded-lg bg-canvas p-1 border border-border/60">
                <TabsTrigger
                  value="password"
                  className="flex items-center gap-1.5 text-xs font-semibold py-1.5 data-[state=active]:bg-white dark:data-[state=active]:bg-surface data-[state=active]:text-primary data-[state=active]:shadow-xs"
                >
                  <Lock className="h-3.5 w-3.5" />
                  <span>{t("auth.passwordTab", "Password")}</span>
                </TabsTrigger>
                <TabsTrigger
                  value="otp"
                  className="flex items-center gap-1.5 text-xs font-semibold py-1.5 data-[state=active]:bg-white dark:data-[state=active]:bg-surface data-[state=active]:text-primary data-[state=active]:shadow-xs"
                >
                  <Phone className="h-3.5 w-3.5" />
                  <span>{t("auth.otpTab", "Phone OTP")}</span>
                </TabsTrigger>
              </TabsList>

              {/* PASSWORD LOGIN FORM */}
              <TabsContent value="password" className="mt-0 space-y-4">
                <form
                  onSubmit={(e) => void passwordForm.handleSubmit(handlePasswordSubmit)(e)}
                  className="space-y-4"
                >
                  <FormField>
                    <FormLabel htmlFor="login-identifier" required>
                      {t("auth.identifierLabel", "Phone or Username")}
                    </FormLabel>
                    <div className="relative">
                      <User
                        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
                        aria-hidden="true"
                      />
                      <Input
                        id="login-identifier"
                        placeholder="+8801XXXXXXXXX"
                        className="h-10 pl-9 text-sm bg-surface"
                        disabled={passwordForm.formState.isSubmitting}
                        {...passwordForm.register("identifier")}
                      />
                    </div>
                    {passwordForm.formState.errors.identifier && (
                      <p className="mt-1 text-xs text-danger font-medium">
                        {t(
                          passwordForm.formState.errors.identifier.message ??
                            "validation.identifierRequired",
                        )}
                      </p>
                    )}
                  </FormField>

                  <FormField>
                    <div className="flex items-center justify-between">
                      <FormLabel htmlFor="login-password" required>
                        {t("auth.passwordLabel", "Password")}
                      </FormLabel>
                      <Link
                        to="/forgot-password"
                        className="text-xs font-medium text-primary hover:underline focus:outline-none focus:ring-1 focus:ring-primary rounded"
                      >
                        {t("auth.forgotPasswordLink", "Forgot password?")}
                      </Link>
                    </div>
                    <div className="relative">
                      <Lock
                        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
                        aria-hidden="true"
                      />
                      <Input
                        id="login-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        className="h-10 pl-9 pr-10 text-sm bg-surface"
                        disabled={passwordForm.formState.isSubmitting}
                        {...passwordForm.register("password")}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={
                          showPassword
                            ? t("auth.hidePassword", "Hide password")
                            : t("auth.showPassword", "Show password")
                        }
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-subtle hover:text-ink focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" aria-hidden="true" />
                        ) : (
                          <Eye className="h-4 w-4" aria-hidden="true" />
                        )}
                      </button>
                    </div>
                    {passwordForm.formState.errors.password && (
                      <p className="mt-1 text-xs text-danger font-medium">
                        {t(
                          passwordForm.formState.errors.password.message ??
                            "validation.passwordRequired",
                        )}
                      </p>
                    )}
                  </FormField>

                  <Button
                    type="submit"
                    size="lg"
                    className="w-full text-sm font-semibold h-10 shadow-xs"
                    disabled={passwordForm.formState.isSubmitting}
                  >
                    {passwordForm.formState.isSubmitting
                      ? t("common.loading", "Signing in...")
                      : t("auth.signInButton", "Sign In")}
                  </Button>
                </form>
              </TabsContent>

              {/* PHONE OTP LOGIN FORM */}
              <TabsContent value="otp" className="mt-0 space-y-4">
                {!otpSent ? (
                  <form
                    onSubmit={(e) => void otpReqForm.handleSubmit(handleOtpRequest)(e)}
                    className="space-y-4"
                  >
                    <FormField>
                      <FormLabel htmlFor="otp-phone" required>
                        {t("auth.phoneLabel", "Mobile Number")}
                      </FormLabel>
                      <div className="relative">
                        <Phone
                          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
                          aria-hidden="true"
                        />
                        <Input
                          id="otp-phone"
                          placeholder="+8801XXXXXXXXX"
                          className="h-10 pl-9 text-sm bg-surface"
                          disabled={otpReqForm.formState.isSubmitting}
                          {...otpReqForm.register("phone")}
                        />
                      </div>
                      {otpReqForm.formState.errors.phone && (
                        <p className="mt-1 text-xs text-danger font-medium">
                          {t(
                            otpReqForm.formState.errors.phone.message ?? "validation.phoneInvalid",
                          )}
                        </p>
                      )}
                    </FormField>

                    <Button
                      type="submit"
                      size="lg"
                      className="w-full text-sm font-semibold h-10 shadow-xs"
                      disabled={otpReqForm.formState.isSubmitting}
                    >
                      {otpReqForm.formState.isSubmitting
                        ? t("common.loading", "Sending OTP...")
                        : t("auth.sendOtpButton", "Send OTP Code")}
                    </Button>
                  </form>
                ) : (
                  <form
                    onSubmit={(e) => void otpVerifyForm.handleSubmit(handleOtpVerify)(e)}
                    className="space-y-4"
                  >
                    <div className="rounded-lg border border-border bg-canvas p-3 text-xs text-ink-muted">
                      <p>
                        {t("auth.otpSentTo", "6-digit OTP code sent to:")}{" "}
                        <span className="font-semibold text-ink">{otpPhone}</span>
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setOtpSent(false);
                          setGeneralError(null);
                        }}
                        className="mt-1 text-xs font-semibold text-primary hover:underline"
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
                        className="h-11 text-center font-mono text-lg tracking-widest bg-surface"
                        disabled={otpVerifyForm.formState.isSubmitting}
                        {...otpVerifyForm.register("code")}
                      />
                      {otpVerifyForm.formState.errors.code && (
                        <p className="mt-1 text-xs text-danger font-medium">
                          {t(
                            otpVerifyForm.formState.errors.code.message ??
                              "validation.otpCodeLength",
                          )}
                        </p>
                      )}
                    </FormField>

                    <Button
                      type="submit"
                      size="lg"
                      className="w-full text-sm font-semibold h-10 shadow-xs"
                      disabled={otpVerifyForm.formState.isSubmitting}
                    >
                      {otpVerifyForm.formState.isSubmitting
                        ? t("common.loading", "Verifying...")
                        : t("auth.verifyOtpButton", "Verify & Sign In")}
                    </Button>
                  </form>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Bottom Bar: System & Compliance Note */}
        <div className="flex flex-col items-center justify-between gap-2 border-t border-border/70 pt-4 text-center text-xs text-ink-subtle sm:flex-row sm:text-left">
          <p>
            {schoolName} &bull; {t("auth.copyright", "All rights reserved.")}
          </p>
          <div className="flex items-center gap-2">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span>v1.0.0 Enterprise</span>
          </div>
        </div>
      </div>
    </div>
  );
}
