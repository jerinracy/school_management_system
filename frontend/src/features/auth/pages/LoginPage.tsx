import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  Award,
  Building2,
  CalendarCheck,
  CheckCircle2,
  CreditCard,
  Eye,
  EyeOff,
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

  // Update page title dynamically
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
            "Two-factor authentication is required for this account. Note: Backend 2FA verify endpoint is currently in development.",
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
    <div className="flex min-h-screen w-full flex-col lg:flex-row bg-surface">
      {/* ========================================================================= */}
      {/* LEFT SHOWCASE / HERO PANEL (Full-Height Institutional Branding, lg+ only) */}
      {/* ========================================================================= */}
      <div className="relative hidden w-full lg:flex lg:w-[50%] xl:w-[54%] flex-col justify-between overflow-hidden bg-gradient-to-br from-slate-950 via-[#0a1826] to-[#042721] p-10 xl:p-14 text-white shadow-2xl">
        {/* Subtle decorative radial light & grid patterns */}
        <div
          className="pointer-events-none absolute -left-20 -top-20 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-20 -right-20 h-96 w-96 rounded-full bg-indigo-500/10 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-10 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:24px_24px]"
          aria-hidden="true"
        />

        {/* Top Header: Official School Brand Identity */}
        <div className="relative z-10 space-y-5">
          <div className="flex items-center gap-4">
            {schoolLogo ? (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/10 p-2 shadow-xl backdrop-blur-md">
                <img
                  src={schoolLogo}
                  alt={schoolName}
                  className="h-full w-full object-contain"
                />
              </div>
            ) : (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-emerald-400/30 bg-gradient-to-tr from-emerald-600 to-teal-500 text-2xl font-black text-white shadow-xl shadow-emerald-950/50">
                {currentLang === "bn" ? "বি" : schoolName.charAt(0).toUpperCase() || "S"}
              </div>
            )}
            <div className="min-w-0">
              <h1 className="text-2xl font-extrabold tracking-tight text-white xl:text-3xl leading-snug">
                {schoolName}
              </h1>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {schoolEIIN && (
                  <span className="inline-flex items-center rounded-md border border-emerald-400/30 bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                    {t("auth.eiinLabel")}: {schoolEIIN}
                  </span>
                )}
                {schoolBoard && (
                  <span className="inline-flex items-center rounded-md border border-white/20 bg-white/10 px-2 py-0.5 text-[11px] font-medium text-slate-300 capitalize">
                    {t("auth.boardLabel")}: {schoolBoard}
                  </span>
                )}
                <span className="inline-flex items-center rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-slate-400">
                  {t("auth.officialPortal")}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Mission & Institutional Highlights */}
        <div className="relative z-10 my-8 space-y-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>Smart Education Management System</span>
            </div>
            <p className="text-xl font-bold leading-relaxed text-slate-100 xl:text-2xl">
              &ldquo;{t("auth.heroQuote")}&rdquo;
            </p>
            <p className="text-xs text-slate-400 xl:text-sm">
              {t("auth.heroTagline")}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3.5 pt-2">
            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-3.5 backdrop-blur-sm transition-all hover:bg-white/[0.07]">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
                <CalendarCheck className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">
                  {t("auth.highlightAttendance")}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Automated shift tracking, device punch ingestion & immediate guardian notification.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-3.5 backdrop-blur-sm transition-all hover:bg-white/[0.07]">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
                <Award className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">
                  {t("auth.highlightGrading")}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Official Bangladesh grading criteria with automated tabulation sheets & printable report cards.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-3.5 backdrop-blur-sm transition-all hover:bg-white/[0.07]">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400">
                <CreditCard className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">
                  {t("auth.highlightFees")}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Instant mobile financial reconciliation, multi-head waiver rules & official money receipts.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Footer: Security & Compliance */}
        <div className="relative z-10 flex items-center justify-between border-t border-white/10 pt-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>256-Bit Encrypted Academic Session</span>
          </div>
          <span>&copy; {new Date().getFullYear()} {schoolName}</span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* RIGHT AUTH PANEL (Full-Height Modern Authentication Workspace)            */}
      {/* ========================================================================= */}
      <div className="flex w-full flex-1 flex-col justify-between bg-surface p-6 sm:p-10 lg:w-[50%] xl:w-[46%] xl:p-14 text-ink">
        {/* Top Bar: Mobile School Logo + Language & Theme Switchers */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          {/* Mobile-only Branding */}
          <div className="flex items-center gap-2.5 lg:hidden">
            {schoolLogo ? (
              <img
                src={schoolLogo}
                alt={schoolName}
                className="h-8 w-8 object-contain rounded-md"
              />
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
                {currentLang === "bn" ? "বি" : schoolName.charAt(0).toUpperCase() || "S"}
              </span>
            )}
            <div className="min-w-0">
              <p className="truncate text-xs font-bold text-ink leading-tight">
                {schoolName}
              </p>
              {schoolEIIN && (
                <p className="text-[10px] text-ink-subtle">
                  {t("auth.eiinLabel")}: {schoolEIIN}
                </p>
              )}
            </div>
          </div>

          <div className="hidden lg:block text-xs font-medium text-ink-muted">
            {t("auth.signInTitle")}
          </div>

          {/* Right Utility Actions */}
          <div className="flex items-center gap-2 ml-auto">
            {/* Language Switcher */}
            <div
              className="inline-flex items-center rounded-lg border border-border bg-canvas p-0.5"
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
                    ? "bg-primary text-white shadow-sm"
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
                    ? "bg-primary text-white shadow-sm"
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
              className="rounded-lg border border-border bg-canvas p-1.5 text-ink-muted transition-colors hover:text-ink"
            >
              {theme === "light" ? (
                <Moon className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Sun className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Center: Auth Form Container */}
        <div className="mx-auto my-auto w-full max-w-md py-8">
          <div className="mb-6 space-y-1.5">
            <div className="inline-flex items-center gap-2 rounded-md bg-primary-soft px-2.5 py-1 text-[11px] font-semibold text-primary">
              <Building2 className="h-3.5 w-3.5" />
              <span>{schoolName}</span>
            </div>
            <h2 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
              {t("auth.welcomeBack")}
            </h2>
            <p className="text-xs text-ink-muted sm:text-sm">
              {t("auth.welcomeBackSubtitle")}
            </p>
          </div>

          {generalError && (
            <div
              className="mb-4 flex items-start gap-2.5 rounded-lg border border-danger/20 bg-danger/10 p-3 text-xs text-danger animate-fade-in"
              role="alert"
            >
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span className="font-medium">{generalError}</span>
            </div>
          )}

          {totpPrompt && (
            <div
              className="mb-4 flex items-start gap-2.5 rounded-lg border border-warning/20 bg-warning/10 p-3 text-xs text-warning animate-fade-in"
              role="alert"
            >
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <span className="font-medium">{totpPrompt}</span>
            </div>
          )}

          <Tabs
            value={activeTab}
            onValueChange={(val) => {
              setActiveTab(val as "password" | "otp");
              setGeneralError(null);
            }}
            className="w-full"
          >
            <TabsList className="mb-5 grid w-full grid-cols-2 rounded-lg bg-canvas p-1">
              <TabsTrigger
                value="password"
                className="flex items-center gap-1.5 text-xs font-semibold py-1.5 data-[state=active]:bg-surface data-[state=active]:text-primary data-[state=active]:shadow-sm"
              >
                <Lock className="h-3.5 w-3.5" />
                <span>{t("auth.passwordTab", "Password")}</span>
              </TabsTrigger>
              <TabsTrigger
                value="otp"
                className="flex items-center gap-1.5 text-xs font-semibold py-1.5 data-[state=active]:bg-surface data-[state=active]:text-primary data-[state=active]:shadow-sm"
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
                    {t("auth.identifierLabel")}
                  </FormLabel>
                  <div className="relative">
                    <User
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle"
                      aria-hidden="true"
                    />
                    <Input
                      id="login-identifier"
                      placeholder="+8801XXXXXXXXX"
                      className="h-10 pl-9 text-sm"
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
                      {t("auth.passwordLabel")}
                    </FormLabel>
                    <Link
                      to="/forgot-password"
                      className="text-xs font-semibold text-primary hover:underline focus:outline-none focus:ring-1 focus:ring-primary rounded"
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
                      className="h-10 pl-9 pr-10 text-sm"
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
                  className="w-full text-sm font-semibold h-10 shadow-sm"
                  disabled={passwordForm.formState.isSubmitting}
                >
                  {passwordForm.formState.isSubmitting
                    ? t("common.loading", "Signing in...")
                    : t("auth.signInButton")}
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
                        className="h-10 pl-9 text-sm"
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
                    className="w-full text-sm font-semibold h-10 shadow-sm"
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
                      className="h-11 text-center font-mono text-lg tracking-widest"
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
                    className="w-full text-sm font-semibold h-10 shadow-sm"
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

        {/* Bottom Bar: System & Compliance Note */}
        <div className="flex flex-col items-center justify-between gap-2 border-t border-border pt-4 text-center text-xs text-ink-subtle sm:flex-row sm:text-left">
          <p>
            {schoolName} &bull; {t("auth.copyright", "All rights reserved.")}
          </p>
          <div className="flex items-center gap-3">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span>v1.0.0 Enterprise</span>
          </div>
        </div>
      </div>
    </div>
  );
}
