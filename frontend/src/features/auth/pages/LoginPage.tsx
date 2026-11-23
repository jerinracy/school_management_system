import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  ArrowRight,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  Lock,
  Moon,
  Phone,
  ShieldAlert,
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
import { AcademicLogo } from "@/features/institutions/components/AcademicLogo";
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

  const {
    fetchBranding,
    getLocalizedName,
    getLogoUrl,
    getEIIN,
    getBoard,
    getLoginBackgroundUrl,
  } = useBrandingStore();

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
  const schoolEIIN = getEIIN();
  const schoolBoard = getBoard();
  const customBackground = getLoginBackgroundUrl();
  const activeBackgroundUrl = customBackground || "/assets/demo-campus.jpg";

  useEffect(() => {
    void fetchBranding();
  }, [fetchBranding]);

  // Update document title dynamically
  useEffect(() => {
    document.title = `${schoolName} — ${t("auth.signInTitle", "Admin Sign In")}`;
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
        } else if (err.details && typeof err.details === "object" && !Array.isArray(err.details)) {
          const firstErr = Object.values(err.details).flat()[0];
          setGeneralError(
            typeof firstErr === "string"
              ? firstErr
              : err.message || t("auth.loginFailed", "Login failed."),
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
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans selection:bg-emerald-800 selection:text-white">
      {/* ======================================================================= */}
      {/* LEFT COLUMN: Majestic Campus Hero & Branding Panel (Desktop Only)       */}
      {/* ======================================================================= */}
      <div className="relative hidden lg:flex flex-col justify-between w-1/2 xl:w-7/12 bg-slate-900 text-white p-10 xl:p-14 overflow-hidden select-none">
        {/* Campus Photograph */}
        <img
          src={activeBackgroundUrl}
          alt={schoolName}
          className="absolute inset-0 h-full w-full object-cover object-center transform scale-105 transition-transform duration-1000"
        />

        {/* High-craft Architectural Scrims */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/70 to-slate-950/40" />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/60 via-transparent to-transparent" />

        {/* 1. Header: Official School Emblem & Metadata */}
        <div className="relative z-10 flex items-center gap-3.5">
          <div className="p-1 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 shadow-sm">
            <AcademicLogo
              logoUrl={schoolLogo}
              name={schoolName}
              size="md"
              className="h-11 w-11 rounded-lg border-none bg-transparent shadow-none"
            />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight leading-snug">
              {schoolName}
            </h2>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              {schoolEIIN && (
                <span>
                  {t("auth.eiinLabel", "EIIN")}: {schoolEIIN}
                </span>
              )}
              {schoolEIIN && schoolBoard && <span>•</span>}
              {schoolBoard && (
                <span>
                  {schoolBoard} {t("auth.boardLabel", "Board")}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 2. Center: Authoritative Academic Statement */}
        <div className="relative z-10 max-w-xl space-y-5 my-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-950/60 backdrop-blur-md px-3.5 py-1 text-xs font-medium text-emerald-300">
            <GraduationCap className="h-4 w-4 text-emerald-400" />
            <span>{t("auth.officialPortal", "Ministry of Education Recognized Portal")}</span>
          </div>

          <h1 className="text-3xl xl:text-4xl font-bold tracking-tight text-white leading-tight">
            {t("auth.heroQuote", "Empowering Educational Excellence & Smart Campus Governance")}
          </h1>

          <p className="text-sm xl:text-base text-slate-300 font-normal leading-relaxed">
            {t("auth.heroTagline", "Unified smart campus operations for Bangladesh schools, madrasahs, and colleges.")}
          </p>

          <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-200">
            <div className="flex items-center gap-2.5 rounded-lg bg-white/5 backdrop-blur-xs border border-white/10 p-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>{t("auth.highlightAttendance", "Live Biometric Attendance & Instant SMS Alerts")}</span>
            </div>
            <div className="flex items-center gap-2.5 rounded-lg bg-white/5 backdrop-blur-xs border border-white/10 p-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>{t("auth.highlightGrading", "National GPA 5.0 Assessment & Instant Tabulation")}</span>
            </div>
          </div>
        </div>

        {/* 3. Footer */}
        <div className="relative z-10 flex items-center justify-between text-xs text-slate-400 border-t border-white/10 pt-4">
          <span>&copy; {new Date().getFullYear()} {schoolName}. {t("auth.copyright", "All rights reserved.")}</span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>v1.0.0 Enterprise</span>
          </span>
        </div>
      </div>

      {/* ======================================================================= */}
      {/* RIGHT COLUMN: Top Bar & Calm, Clean Authentication Card                 */}
      {/* ======================================================================= */}
      <div className="relative flex flex-col justify-between w-full lg:w-1/2 xl:w-5/12 min-h-screen p-6 sm:p-10 lg:p-12 bg-slate-50 dark:bg-slate-950">
        {/* Top Utility Bar: Administrative Indicator & Language/Theme Toggles */}
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
            <Building2 className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
            <span>{t("auth.administrativeAccess", "Administrative Access")}</span>
          </div>

          <div className="flex items-center gap-2">
            {/* Language Switcher */}
            <div
              className="inline-flex items-center rounded-lg border border-slate-200/90 bg-white dark:bg-slate-900 p-0.5 shadow-2xs"
              role="group"
              aria-label={t("app.language.label")}
            >
              <button
                type="button"
                onClick={() => setAppLanguage("en")}
                aria-pressed={currentLang === "en"}
                aria-label={t("app.language.switchToEnglish")}
                className={cn(
                  "rounded-md px-2.5 py-0.5 text-[11px] font-bold transition-all",
                  currentLang === "en"
                    ? "bg-emerald-800 text-white shadow-2xs"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100",
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
                  "rounded-md px-2.5 py-0.5 text-[11px] font-bold transition-all",
                  currentLang === "bn"
                    ? "bg-emerald-800 text-white shadow-2xs"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100",
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
              className="rounded-lg border border-slate-200/90 bg-white dark:bg-slate-900 p-1.5 text-slate-600 dark:text-slate-400 transition-colors hover:text-slate-900 dark:hover:text-slate-100 shadow-2xs"
            >
              {theme === "light" ? (
                <Moon className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <Sun className="h-3.5 w-3.5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Centered Authentication Card */}
        <div className="my-auto w-full max-w-[420px] mx-auto py-8">
          {/* Mobile-only School Branding Header */}
          <div className="lg:hidden flex flex-col items-center text-center mb-6">
            <div className="inline-flex items-center justify-center rounded-xl border border-emerald-200/90 bg-emerald-50/80 dark:bg-emerald-950/40 p-2 mb-2 shadow-xs">
              <AcademicLogo
                logoUrl={schoolLogo}
                name={schoolName}
                size="md"
                className="h-10 w-10 rounded-lg border-none bg-transparent shadow-none"
              />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {schoolName}
            </h2>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
              {schoolEIIN && <span>{t("auth.eiinLabel", "EIIN")}: {schoolEIIN}</span>}
              {schoolEIIN && schoolBoard && <span>•</span>}
              {schoolBoard && <span>{schoolBoard} {t("auth.boardLabel", "Board")}</span>}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 shadow-sm">
            <div className="mb-6 space-y-1">
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                {t("auth.signInTitle", "Admin Sign In")}
              </h2>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                {t("auth.signInSubtitle", "Access your institution academic and administrative workspace.")}
              </p>
            </div>

            {generalError && (
              <div
                className="mb-4 flex items-start gap-2 rounded-xl border border-danger/20 bg-danger/10 p-3 text-xs text-danger animate-fade-in"
                role="alert"
              >
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span className="font-medium">{generalError}</span>
              </div>
            )}

            {totpPrompt && (
              <div
                className="mb-4 flex items-start gap-2 rounded-xl border border-warning/20 bg-warning/10 p-3 text-xs text-warning animate-fade-in"
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
              <TabsList className="mb-4 grid w-full grid-cols-2 rounded-xl bg-slate-100 dark:bg-slate-800 p-1 border border-slate-200/60 dark:border-slate-700/60">
                <TabsTrigger
                  value="password"
                  className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:text-slate-900 dark:data-[state=active]:text-slate-100 data-[state=active]:shadow-xs transition-all text-slate-600 dark:text-slate-400"
                >
                  <Lock className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
                  <span>{t("auth.passwordTab", "Password")}</span>
                </TabsTrigger>
                <TabsTrigger
                  value="otp"
                  className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-slate-900 data-[state=active]:text-slate-900 dark:data-[state=active]:text-slate-100 data-[state=active]:shadow-xs transition-all text-slate-600 dark:text-slate-400"
                >
                  <Phone className="h-3.5 w-3.5" />
                  <span>{t("auth.otpTab", "Phone OTP")}</span>
                </TabsTrigger>
              </TabsList>

              {/* =============================================================== */}
              {/* PASSWORD LOGIN FORM                                             */}
              {/* =============================================================== */}
              <TabsContent value="password" className="mt-0 space-y-4">
                <form
                  onSubmit={(e) => void passwordForm.handleSubmit(handlePasswordSubmit)(e)}
                  className="space-y-4"
                >
                  <FormField>
                    <FormLabel htmlFor="login-identifier" required className="text-xs font-medium text-slate-900 dark:text-slate-100">
                      {t("auth.identifierLabel", "Phone or Username")}
                    </FormLabel>
                    <div className="relative mt-1">
                      <User
                        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                        aria-hidden="true"
                      />
                      <Input
                        id="login-identifier"
                        placeholder="+8801XXXXXXXXX"
                        className="h-10 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pl-9 text-xs sm:text-sm placeholder:text-slate-400/60 focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                      <FormLabel htmlFor="login-password" required className="text-xs font-medium text-slate-900 dark:text-slate-100">
                        {t("auth.passwordLabel", "Password")}
                      </FormLabel>
                      <Link
                        to="/forgot-password"
                        className="text-xs font-medium text-emerald-800 dark:text-emerald-400 hover:underline focus:outline-none focus:ring-1 focus:ring-emerald-600 rounded"
                      >
                        {t("auth.forgotPasswordLink", "Forgot password?")}
                      </Link>
                    </div>
                    <div className="relative mt-1">
                      <Lock
                        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                        aria-hidden="true"
                      />
                      <Input
                        id="login-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        className="h-10 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pl-9 pr-9 text-xs sm:text-sm placeholder:text-slate-400/60 focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-600 transition-colors"
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
                    className="w-full text-xs sm:text-sm font-semibold h-10 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white shadow-sm transition-all active:scale-[0.99] mt-2 flex items-center justify-center gap-2"
                    disabled={passwordForm.formState.isSubmitting}
                  >
                    <span>
                      {passwordForm.formState.isSubmitting
                        ? t("common.loading", "Signing in...")
                        : t("auth.signInButton", "Sign In")}
                    </span>
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </form>
              </TabsContent>

              {/* =============================================================== */}
              {/* PHONE OTP LOGIN FORM                                            */}
              {/* =============================================================== */}
              <TabsContent value="otp" className="mt-0 space-y-4">
                {!otpSent ? (
                  <form
                    onSubmit={(e) => void otpReqForm.handleSubmit(handleOtpRequest)(e)}
                    className="space-y-4"
                  >
                    <FormField>
                      <FormLabel htmlFor="otp-phone" required className="text-xs font-medium text-slate-900 dark:text-slate-100">
                        {t("auth.phoneLabel", "Mobile Number")}
                      </FormLabel>
                      <div className="relative mt-1">
                        <Phone
                          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                          aria-hidden="true"
                        />
                        <Input
                          id="otp-phone"
                          placeholder="+8801XXXXXXXXX"
                          className="h-10 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pl-9 text-xs sm:text-sm placeholder:text-slate-400/60 focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                      className="w-full text-xs sm:text-sm font-semibold h-10 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white shadow-sm transition-all active:scale-[0.99] mt-2 flex items-center justify-center gap-2"
                      disabled={otpReqForm.formState.isSubmitting}
                    >
                      <span>
                        {otpReqForm.formState.isSubmitting
                          ? t("common.loading", "Sending OTP...")
                          : t("auth.sendOtpButton", "Send OTP Code")}
                      </span>
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </form>
                ) : (
                  <form
                    onSubmit={(e) => void otpVerifyForm.handleSubmit(handleOtpVerify)(e)}
                    className="space-y-4"
                  >
                    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-emerald-50/50 dark:bg-emerald-950/30 p-3 text-xs text-slate-600 dark:text-slate-300">
                      <p>
                        {t("auth.otpSentTo", "6-digit OTP code sent to:")}{" "}
                        <span className="font-semibold text-slate-900 dark:text-slate-100">{otpPhone}</span>
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setOtpSent(false);
                          setGeneralError(null);
                        }}
                        className="mt-1 text-xs font-semibold text-emerald-800 dark:text-emerald-400 hover:underline"
                      >
                        {t("auth.changePhone", "Change number")}
                      </button>
                    </div>

                    <FormField>
                      <FormLabel htmlFor="otp-code" required className="text-xs font-medium text-slate-900 dark:text-slate-100">
                        {t("auth.otpCodeLabel", "Enter 6-digit Code")}
                      </FormLabel>
                      <div className="relative mt-1">
                        <Input
                          id="otp-code"
                          placeholder="123456"
                          maxLength={6}
                          className="h-10 rounded-lg text-center font-mono text-base tracking-widest border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 placeholder:text-slate-400/40 focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
                          disabled={otpVerifyForm.formState.isSubmitting}
                          {...otpVerifyForm.register("code")}
                        />
                      </div>
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
                      className="w-full text-xs sm:text-sm font-semibold h-10 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white shadow-sm transition-all active:scale-[0.99] mt-2 flex items-center justify-center gap-2"
                      disabled={otpVerifyForm.formState.isSubmitting}
                    >
                      <span>
                        {otpVerifyForm.formState.isSubmitting
                          ? t("common.loading", "Verifying...")
                          : t("auth.verifyOtpButton", "Verify & Sign In")}
                      </span>
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </form>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-slate-400 dark:text-slate-500 pt-4 border-t border-slate-200/60 dark:border-slate-800/60">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>{t("auth.curriculumCompliant", "Ministry of Education Curriculum Compliant")}</span>
          </div>
          <span className="lg:hidden">&copy; {new Date().getFullYear()} {schoolName}</span>
        </div>
      </div>
    </div>
  );
}
