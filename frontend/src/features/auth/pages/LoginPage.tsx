import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Building2,
  CalendarDays,
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
  UsersRound,
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
    <div className="relative min-h-screen lg:h-screen lg:max-h-screen w-full flex flex-col justify-between overflow-x-hidden lg:overflow-hidden bg-[#F8FDF9] dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
      {/* ========================================================================= */}
      {/* FLOWING WAVES BACKGROUND (Behind the entire layout & lower-left image)     */}
      {/* ========================================================================= */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        {/* Soft mint ambient glow top right */}
        <div className="absolute -top-32 -right-32 h-[500px] w-[500px] rounded-full bg-emerald-200/25 dark:bg-emerald-950/20 blur-3xl" />
        <div className="absolute top-1/4 -left-32 h-[450px] w-[450px] rounded-full bg-emerald-100/30 dark:bg-emerald-900/10 blur-3xl" />

        {/* Dynamic Curved Flowing Waves at the bottom */}
        <svg
          className="absolute bottom-0 left-0 w-full h-[220px] lg:h-[280px] opacity-80 dark:opacity-20 transition-opacity"
          viewBox="0 0 1440 480"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="none"
        >
          {/* Pale background wave layer */}
          <path
            d="M0 240C240 340 480 370 720 300C960 230 1200 240 1440 280V480H0V240Z"
            fill="#EAF8EE"
            fillOpacity="0.75"
          />
          {/* Middle translucent white/mint wave */}
          <path
            d="M0 310C280 230 560 360 840 320C1120 280 1300 370 1440 350V480H0V310Z"
            fill="#D8F3E1"
            fillOpacity="0.55"
          />
          {/* Foreground soft wave crest */}
          <path
            d="M0 380C320 310 640 430 960 360C1280 290 1380 400 1440 410V480H0V380Z"
            fill="#F4FCF6"
            fillOpacity="0.85"
          />
        </svg>
      </div>

      {/* ========================================================================= */}
      {/* MAIN TWO-COLUMN BODY CONTENT                                              */}
      {/* ========================================================================= */}
      <div className="relative z-10 flex flex-1 min-h-0 flex-col lg:flex-row w-full px-4 sm:px-8 lg:px-10 xl:px-14 py-2 sm:py-3 lg:py-3.5 max-w-[1600px] mx-auto items-stretch">
        {/* ======================================================================= */}
        {/* LEFT COLUMN: School Branding, Feature Highlights & Campus Photo (~55%)  */}
        {/* ======================================================================= */}
        <div className="relative flex flex-col justify-between w-full lg:w-[55%] pr-0 lg:pr-8 xl:pr-12 pt-1 pb-2 sm:pb-3">
          <div className="space-y-3 xl:space-y-3.5">
            {/* 1. Official Portal Badge */}
            <div>
              <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300/80 bg-emerald-50/90 dark:bg-emerald-950/50 px-3 py-1 text-[11px] font-semibold text-emerald-800 dark:text-emerald-300 shadow-2xs">
                <GraduationCap className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
                <span>{t("auth.officialPortal", "Government EIIN Compliant Official Portal")}</span>
              </div>
            </div>

            {/* 2. School Logo Container */}
            <div className="pt-0.5">
              <div className="inline-flex items-center justify-center rounded-xl border border-emerald-200/90 bg-emerald-50/80 dark:bg-emerald-950/40 p-2 shadow-xs">
                <AcademicLogo
                  logoUrl={schoolLogo}
                  name={schoolName}
                  size="md"
                  className="h-11 w-11 xl:h-12 xl:w-12 rounded-lg border-none bg-transparent shadow-none"
                />
              </div>
            </div>

            {/* 3. School Name */}
            <div className="space-y-1.5">
              <h1 className="text-2xl sm:text-3xl xl:text-[34px] font-extrabold tracking-tight text-slate-900 dark:text-slate-100 leading-snug max-w-xl">
                {schoolName}
              </h1>

              {/* 4. Three Badges: EIIN, Board, Authorized Portal */}
              <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                {schoolEIIN && (
                  <span className="inline-flex items-center rounded-md border border-slate-200 bg-white dark:bg-slate-900 px-2.5 py-0.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300 shadow-2xs">
                    {t("auth.eiinLabel", "EIIN")}: {schoolEIIN}
                  </span>
                )}
                {schoolBoard && (
                  <span className="inline-flex items-center rounded-md border border-slate-200 bg-white dark:bg-slate-900 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 dark:text-slate-400 capitalize shadow-2xs">
                    {schoolBoard} {t("auth.boardLabel", "Board")}
                  </span>
                )}
                <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-300/80 bg-emerald-50/90 dark:bg-emerald-950/40 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 dark:text-emerald-300 shadow-2xs">
                  <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                  <span>{t("auth.authorizedPortal", "Authorized Portal")}</span>
                </span>
              </div>

              {/* Green Accent Line */}
              <div className="w-10 h-0.5 bg-emerald-800 dark:bg-emerald-500 rounded-full mt-2 mb-1.5" />

              {/* 5. Institutional Description */}
              <p className="max-w-lg text-xs sm:text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
                {t(
                  "auth.institutionDescription",
                  "Academic Administration, Student Information & Smart Campus Management System.",
                )}
              </p>
            </div>

            {/* 6. Four Compact Feature Highlights (Horizontally Aligned) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 max-w-xl">
              {/* Feature 1: Student Management */}
              <div className="group rounded-xl border border-emerald-200/60 bg-emerald-50/50 dark:bg-emerald-950/30 p-2 xl:p-2.5 flex flex-col items-center text-center transition-all hover:bg-emerald-50 hover:shadow-2xs">
                <div className="flex h-7 w-7 xl:h-8 xl:w-8 items-center justify-center rounded-lg bg-emerald-100/80 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 mb-1 transition-transform group-hover:scale-105">
                  <UsersRound className="h-3.5 w-3.5" />
                </div>
                <span className="text-[10px] xl:text-[11px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                  {t("auth.featureStudentManagement", "Student Management")}
                </span>
              </div>

              {/* Feature 2: Academic Management */}
              <div className="group rounded-xl border border-emerald-200/60 bg-emerald-50/50 dark:bg-emerald-950/30 p-2 xl:p-2.5 flex flex-col items-center text-center transition-all hover:bg-emerald-50 hover:shadow-2xs">
                <div className="flex h-7 w-7 xl:h-8 xl:w-8 items-center justify-center rounded-lg bg-emerald-100/80 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 mb-1 transition-transform group-hover:scale-105">
                  <GraduationCap className="h-3.5 w-3.5" />
                </div>
                <span className="text-[10px] xl:text-[11px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                  {t("auth.featureAcademicManagement", "Academic Management")}
                </span>
              </div>

              {/* Feature 3: Attendance & Leave */}
              <div className="group rounded-xl border border-emerald-200/60 bg-emerald-50/50 dark:bg-emerald-950/30 p-2 xl:p-2.5 flex flex-col items-center text-center transition-all hover:bg-emerald-50 hover:shadow-2xs">
                <div className="flex h-7 w-7 xl:h-8 xl:w-8 items-center justify-center rounded-lg bg-emerald-100/80 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 mb-1 transition-transform group-hover:scale-105">
                  <CalendarDays className="h-3.5 w-3.5" />
                </div>
                <span className="text-[10px] xl:text-[11px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                  {t("auth.featureAttendanceLeave", "Attendance & Leave")}
                </span>
              </div>

              {/* Feature 4: Reports & Analytics */}
              <div className="group rounded-xl border border-emerald-200/60 bg-emerald-50/50 dark:bg-emerald-950/30 p-2 xl:p-2.5 flex flex-col items-center text-center transition-all hover:bg-emerald-50 hover:shadow-2xs">
                <div className="flex h-7 w-7 xl:h-8 xl:w-8 items-center justify-center rounded-lg bg-emerald-100/80 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 mb-1 transition-transform group-hover:scale-105">
                  <BarChart3 className="h-3.5 w-3.5" />
                </div>
                <span className="text-[10px] xl:text-[11px] font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                  {t("auth.featureReportsAnalytics", "Reports & Analytics")}
                </span>
              </div>
            </div>
          </div>

          {/* ===================================================================== */}
          {/* 7. Dynamic School Background Image with CSS Multi-Directional Mask   */}
          {/* ===================================================================== */}
          <div className="relative mt-2 xl:mt-3 hidden sm:block w-full max-w-lg">
            <div className="relative h-[120px] sm:h-[135px] lg:h-[150px] xl:h-[175px] w-full overflow-hidden rounded-xl">
              <img
                src={activeBackgroundUrl}
                alt={schoolName}
                className="h-full w-full object-cover object-bottom transition-opacity duration-500"
                style={{
                  WebkitMaskImage:
                    "linear-gradient(to bottom, transparent 0%, black 25%), linear-gradient(to right, black 0%, black 65%, transparent 100%)",
                  maskImage:
                    "linear-gradient(to bottom, transparent 0%, black 25%), linear-gradient(to right, black 0%, black 65%, transparent 100%)",
                  WebkitMaskComposite: "source-in",
                  maskComposite: "intersect",
                }}
              />
            </div>

            {/* Carousel indicator dots */}
            <div className="mt-1.5 flex items-center justify-start gap-1.5 pl-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-800 dark:bg-emerald-400" />
              <span className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700" />
              <span className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700" />
            </div>
          </div>
        </div>

        {/* ======================================================================= */}
        {/* RIGHT COLUMN: Top Bar & Centered Authentication Card (~45%)            */}
        {/* ======================================================================= */}
        <div className="relative flex flex-col justify-between w-full lg:w-[45%] pl-0 lg:pl-6 xl:pl-8 pt-1 pb-2 sm:pb-3">
          {/* Top Utility Bar: Administrative Access & Language/Theme Toggles */}
          <div className="flex items-center justify-between pb-2 xl:pb-3 w-full">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
              <Building2 className="h-3.5 w-3.5 text-emerald-800 dark:text-emerald-400" />
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
                className="rounded-lg border border-slate-200/90 bg-white dark:bg-slate-900 p-1 text-slate-600 dark:text-slate-400 transition-colors hover:text-slate-900 dark:hover:text-slate-100 shadow-2xs"
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
          <div className="mx-auto my-auto w-full max-w-[420px] xl:max-w-[440px]">
            <div className="rounded-2xl border border-slate-100 dark:border-slate-800/80 bg-white dark:bg-slate-900 p-5 sm:p-6 xl:p-7 shadow-lg shadow-slate-200/50 dark:shadow-none transition-shadow">
              {/* Card Header: School Logo & Title */}
              <div className="flex flex-col items-center text-center mb-3 xl:mb-4">
                <div className="inline-flex items-center justify-center rounded-xl border border-emerald-200/90 bg-emerald-50/80 dark:bg-emerald-950/40 p-1.5 mb-2 shadow-2xs">
                  <AcademicLogo
                    logoUrl={schoolLogo}
                    name={schoolName}
                    size="md"
                    className="h-9 w-9 xl:h-10 xl:w-10 rounded-lg border-none bg-transparent shadow-none"
                  />
                </div>

                <h2 className="text-lg xl:text-xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 leading-snug">
                  {schoolName}
                </h2>
                <p className="mt-0.5 text-[11px] sm:text-xs font-medium text-slate-500">
                  {t("auth.subTitleSms", "School Management System")}
                </p>
              </div>

              {/* "Admin Sign In" Divider */}
              <div className="relative mb-3 xl:mb-4">
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="w-full border-t border-slate-200 dark:border-slate-800" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-white dark:bg-slate-900 px-3 font-semibold text-slate-700 dark:text-slate-300 text-[11px]">
                    {t("auth.signInTitle", "Admin Sign In")}
                  </span>
                </div>
              </div>

              {generalError && (
                <div
                  className="mb-3 flex items-start gap-2 rounded-xl border border-danger/20 bg-danger/10 p-2.5 text-xs text-danger animate-fade-in"
                  role="alert"
                >
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  <span className="font-medium">{generalError}</span>
                </div>
              )}

              {totpPrompt && (
                <div
                  className="mb-3 flex items-start gap-2 rounded-xl border border-warning/20 bg-warning/10 p-2.5 text-xs text-warning animate-fade-in"
                  role="alert"
                >
                  <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
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
                <TabsList className="mb-3 xl:mb-4 grid w-full grid-cols-2 rounded-xl bg-slate-100/90 dark:bg-slate-800/60 p-0.5 border border-slate-200/60">
                  <TabsTrigger
                    value="password"
                    className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-emerald-50 dark:data-[state=active]:bg-emerald-950/60 data-[state=active]:text-emerald-900 dark:data-[state=active]:text-emerald-300 data-[state=active]:border data-[state=active]:border-emerald-300/60 data-[state=active]:shadow-xs transition-all text-slate-600 dark:text-slate-400"
                  >
                    <Lock className="h-3.5 w-3.5 text-emerald-800 dark:text-emerald-400" />
                    <span>{t("auth.passwordTab", "Password")}</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="otp"
                    className="flex items-center justify-center gap-1.5 text-xs font-semibold py-1.5 rounded-lg data-[state=active]:bg-emerald-50 dark:data-[state=active]:bg-emerald-950/60 data-[state=active]:text-emerald-900 dark:data-[state=active]:text-emerald-300 data-[state=active]:border data-[state=active]:border-emerald-300/60 data-[state=active]:shadow-xs transition-all text-slate-600 dark:text-slate-400"
                  >
                    <Phone className="h-3.5 w-3.5" />
                    <span>{t("auth.otpTab", "Phone OTP")}</span>
                  </TabsTrigger>
                </TabsList>

                {/* =============================================================== */}
                {/* PASSWORD LOGIN FORM                                             */}
                {/* =============================================================== */}
                <TabsContent value="password" className="mt-0 space-y-3">
                  <form
                    onSubmit={(e) => void passwordForm.handleSubmit(handlePasswordSubmit)(e)}
                    className="space-y-3"
                  >
                    <FormField>
                      <FormLabel htmlFor="login-identifier" required className="text-[11px] font-medium text-slate-900 dark:text-slate-100">
                        {t("auth.identifierLabel", "Phone or Username")}
                      </FormLabel>
                      <div className="relative mt-1">
                        <User
                          className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
                          aria-hidden="true"
                        />
                        <Input
                          id="login-identifier"
                          placeholder="+8801XXXXXXXXX"
                          className="h-10 xl:h-11 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pl-9 text-xs xl:text-sm placeholder:text-slate-400/50 placeholder:font-normal focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                        <FormLabel htmlFor="login-password" required className="text-[11px] font-medium text-slate-900 dark:text-slate-100">
                          {t("auth.passwordLabel", "Password")}
                        </FormLabel>
                        <Link
                          to="/forgot-password"
                          className="text-[11px] font-medium text-emerald-800 dark:text-emerald-400 hover:underline focus:outline-none focus:ring-1 focus:ring-emerald-600 rounded"
                        >
                          {t("auth.forgotPasswordLink", "Forgot password?")}
                        </Link>
                      </div>
                      <div className="relative mt-1">
                        <Lock
                          className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
                          aria-hidden="true"
                        />
                        <Input
                          id="login-password"
                          type={showPassword ? "text" : "password"}
                          placeholder="••••••••"
                          className="h-10 xl:h-11 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pl-9 pr-9 text-xs xl:text-sm placeholder:text-slate-400/50 placeholder:font-normal focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                            <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
                          ) : (
                            <Eye className="h-3.5 w-3.5" aria-hidden="true" />
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
                      className="w-full text-xs xl:text-sm font-semibold h-10 xl:h-11 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white shadow-md shadow-emerald-950/15 transition-all active:scale-[0.99] mt-2 flex items-center justify-center gap-2"
                      disabled={passwordForm.formState.isSubmitting}
                    >
                      <span>
                        {passwordForm.formState.isSubmitting
                          ? t("common.loading", "Signing in...")
                          : t("auth.signInButton", "Sign In")}
                      </span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </form>
                </TabsContent>

                {/* =============================================================== */}
                {/* PHONE OTP LOGIN FORM                                            */}
                {/* =============================================================== */}
                <TabsContent value="otp" className="mt-0 space-y-3">
                  {!otpSent ? (
                    <form
                      onSubmit={(e) => void otpReqForm.handleSubmit(handleOtpRequest)(e)}
                      className="space-y-3"
                    >
                      <FormField>
                        <FormLabel htmlFor="otp-phone" required className="text-[11px] font-medium text-slate-900 dark:text-slate-100">
                          {t("auth.phoneLabel", "Mobile Number")}
                        </FormLabel>
                        <div className="relative mt-1">
                          <Phone
                            className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
                            aria-hidden="true"
                          />
                          <Input
                            id="otp-phone"
                            placeholder="+8801XXXXXXXXX"
                            className="h-10 xl:h-11 rounded-lg border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pl-9 text-xs xl:text-sm placeholder:text-slate-400/50 placeholder:font-normal focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                        className="w-full text-xs xl:text-sm font-semibold h-10 xl:h-11 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white shadow-md shadow-emerald-950/15 transition-all active:scale-[0.99] mt-2 flex items-center justify-center gap-2"
                        disabled={otpReqForm.formState.isSubmitting}
                      >
                        <span>
                          {otpReqForm.formState.isSubmitting
                            ? t("common.loading", "Sending OTP...")
                            : t("auth.sendOtpButton", "Send OTP Code")}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </form>
                  ) : (
                    <form
                      onSubmit={(e) => void otpVerifyForm.handleSubmit(handleOtpVerify)(e)}
                      className="space-y-3"
                    >
                      <div className="rounded-lg border border-slate-200 bg-emerald-50/50 p-2.5 text-xs text-slate-600">
                        <p>
                          {t("auth.otpSentTo", "6-digit OTP code sent to:")}{" "}
                          <span className="font-semibold text-slate-900">{otpPhone}</span>
                        </p>
                        <button
                          type="button"
                          onClick={() => {
                            setOtpSent(false);
                            setGeneralError(null);
                          }}
                          className="mt-1 text-xs font-semibold text-emerald-800 hover:underline"
                        >
                          {t("auth.changePhone", "Change number")}
                        </button>
                      </div>

                      <FormField>
                        <FormLabel htmlFor="otp-code" required className="text-[11px] font-medium text-slate-900 dark:text-slate-100">
                          {t("auth.otpCodeLabel", "Enter 6-digit Code")}
                        </FormLabel>
                        <div className="relative mt-1">
                          <Input
                            id="otp-code"
                            placeholder="123456"
                            maxLength={6}
                            className="h-10 xl:h-11 rounded-lg text-center font-mono text-base tracking-widest border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 placeholder:text-slate-400/40 focus-visible:border-emerald-600 focus-visible:ring-2 focus-visible:ring-emerald-600/15 transition-all shadow-2xs"
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
                        className="w-full text-xs xl:text-sm font-semibold h-10 xl:h-11 rounded-lg bg-emerald-800 hover:bg-emerald-900 text-white shadow-md shadow-emerald-950/15 transition-all active:scale-[0.99] mt-2 flex items-center justify-center gap-2"
                        disabled={otpVerifyForm.formState.isSubmitting}
                      >
                        <span>
                          {otpVerifyForm.formState.isSubmitting
                            ? t("common.loading", "Verifying...")
                            : t("auth.verifyOtpButton", "Verify & Sign In")}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </form>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 8. FULL-WIDTH FOOTER                                                      */}
      {/* ========================================================================= */}
      <footer className="relative z-10 w-full border-t border-slate-200/70 bg-white/60 dark:bg-slate-950/60 backdrop-blur-xs px-4 sm:px-8 py-2">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-1.5 text-[11px] text-slate-500 dark:text-slate-400 max-w-[1600px] mx-auto">
          {/* Left: Ministry Compliance */}
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            <span>{t("auth.curriculumCompliant", "Ministry of Education Curriculum Compliant")}</span>
          </div>

          {/* Center: Dynamic Copyright */}
          <div className="text-center">
            <span>&copy; {new Date().getFullYear()} {schoolName}. {t("auth.copyright", "All rights reserved.")}</span>
          </div>

          {/* Right: Version and Status */}
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-600" />
            <span>v1.0.0 Enterprise</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
