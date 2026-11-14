import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  CheckCircle2,
  Globe,
  KeyRound,
  Laptop,
  LogOut,
  Shield,
  Smartphone,
  User,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { PageHeader } from "@/components/composite/PageHeader";
import { setAppLanguage } from "@/i18n";
import { formatDate, formatTimeShort } from "@/lib/format";
import { ApiError } from "@/lib/errors";
import { authApi } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/store/authStore";
import {
  changePasswordSchema,
  type ChangePasswordFormData,
} from "@/features/auth/schemas/authSchemas";

interface SessionItem {
  id: string;
  ip_address: string;
  device_name: string;
  platform: string;
  last_activity: string;
  is_active: boolean;
}

export function ProfilePage() {
  const { t, i18n } = useTranslation();
  const { user, updateUserPreferences, logout } = useAuthStore();

  const [pwSuccess, setPwSuccess] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);

  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [sessionToRevoke, setSessionToRevoke] = useState<string | null>(null);
  const [showLogoutAllConfirm, setShowLogoutAllConfirm] = useState(false);

  // Change password form
  const pwForm = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { old_password: "", new_password: "", confirm_password: "" },
  });

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const data = await authApi.getSessions();
      if (Array.isArray(data)) {
        setSessions(data as SessionItem[]);
      } else if (data && typeof data === "object" && "results" in data && Array.isArray((data as { results: unknown[] }).results)) {
        setSessions((data as { results: unknown[] }).results as SessionItem[]);
      }
    } catch {
      // Ignore sessions loading error
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    void loadSessions();
  }, []);

  const handleChangePassword = async (data: ChangePasswordFormData) => {
    setPwError(null);
    setPwSuccess(null);
    try {
      await authApi.changePassword({
        old_password: data.old_password,
        new_password: data.new_password,
      });
      setPwSuccess(t("auth.passwordChangedSuccess", "Password updated successfully."));
      pwForm.reset();
    } catch (err) {
      if (err instanceof ApiError) {
        setPwError(err.message || t("auth.passwordChangeFailed", "Failed to update password."));
      } else {
        setPwError(t("auth.passwordChangeFailed", "Failed to update password."));
      }
    }
  };

  const handleLanguageChange = async (lng: "bn" | "en") => {
    setAppLanguage(lng);
    updateUserPreferences({ language_preference: lng });
    try {
      await authApi.updateMe({ language_preference: lng });
      toast.success(t("profile.languageUpdated", "Language preference saved."));
    } catch {
      // Language updated locally in i18n
    }
  };

  const handleRevokeSession = async () => {
    if (!sessionToRevoke) return;
    try {
      await authApi.revokeSession(sessionToRevoke);
      toast.success(t("profile.sessionRevoked", "Session terminated."));
      setSessions((prev) => prev.filter((s) => s.id !== sessionToRevoke));
    } catch {
      toast.error(t("profile.sessionRevokeFailed", "Failed to revoke session."));
    } finally {
      setSessionToRevoke(null);
    }
  };

  const handleLogoutAll = async () => {
    try {
      await authApi.logoutAll();
      toast.success(t("profile.loggedOutAll", "All sessions terminated."));
      logout();
    } catch {
      toast.error(t("profile.logoutAllFailed", "Failed to terminate all sessions."));
    } finally {
      setShowLogoutAllConfirm(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("profile.title", "My Profile & Security")}
        subtitle={t("profile.subtitle", "Manage your account settings, credentials, and active login sessions.")}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Profile Card */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <User className="h-4 w-4 text-primary" />
              {t("profile.accountInfo", "Account Details")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs text-ink-muted">{t("profile.name", "Full Name")}</p>
              <p className="text-sm font-semibold text-ink">{user?.full_name || user?.username || "—"}</p>
            </div>

            <div>
              <p className="text-xs text-ink-muted">{t("profile.phone", "Phone Number")}</p>
              <p className="text-sm font-medium text-ink font-mono">{user?.phone || "—"}</p>
            </div>

            <div>
              <p className="text-xs text-ink-muted">{t("profile.email", "Email Address")}</p>
              <p className="text-sm font-medium text-ink">{user?.email || "—"}</p>
            </div>

            <div>
              <p className="text-xs text-ink-muted">{t("profile.userType", "Role & User Type")}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                <span className="inline-flex items-center rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                  {user?.user_type}
                </span>
                {user?.roles?.map((r) => (
                  <span key={r} className="inline-flex items-center rounded bg-surface border border-border px-1.5 py-0.5 text-[11px] text-ink-muted">
                    {r}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-border">
              <FormField>
                <FormLabel htmlFor="language_preference" className="flex items-center gap-1.5">
                  <Globe className="h-3.5 w-3.5 text-ink-muted" />
                  {t("profile.preferredLanguage", "Preferred Language")}
                </FormLabel>
                <Select
                  value={i18n.language === "bn" ? "bn" : "en"}
                  onValueChange={(val) => void handleLanguageChange(val as "bn" | "en")}
                >
                  <SelectTrigger id="language_preference">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bn">বাংলা (Bengali)</SelectItem>
                    <SelectItem value="en">English</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
            </div>
          </CardContent>
        </Card>

        {/* Change Password Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-primary" />
              {t("profile.changePassword", "Change Password")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pwSuccess && (
              <div className="mb-4 flex items-center gap-2 rounded-md bg-success/10 p-2.5 text-xs text-success">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{pwSuccess}</span>
              </div>
            )}
            {pwError && (
              <div className="mb-4 flex items-center gap-2 rounded-md bg-danger/10 p-2.5 text-xs text-danger">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{pwError}</span>
              </div>
            )}

            <form onSubmit={(e) => void pwForm.handleSubmit(handleChangePassword)(e)} className="space-y-3 max-w-md">
              <FormField>
                <FormLabel htmlFor="profile-old-pw" required>
                  {t("auth.currentPassword", "Current Password")}
                </FormLabel>
                <Input
                  id="profile-old-pw"
                  type="password"
                  placeholder="••••••••"
                  disabled={pwForm.formState.isSubmitting}
                  {...pwForm.register("old_password")}
                />
                {pwForm.formState.errors.old_password && (
                  <p className="mt-1 text-xs text-danger">{t(pwForm.formState.errors.old_password.message ?? "")}</p>
                )}
              </FormField>

              <FormField>
                <FormLabel htmlFor="profile-new-pw" required>
                  {t("auth.newPassword", "New Password")}
                </FormLabel>
                <Input
                  id="profile-new-pw"
                  type="password"
                  placeholder="••••••••"
                  disabled={pwForm.formState.isSubmitting}
                  {...pwForm.register("new_password")}
                />
                {pwForm.formState.errors.new_password && (
                  <p className="mt-1 text-xs text-danger">{t(pwForm.formState.errors.new_password.message ?? "")}</p>
                )}
              </FormField>

              <FormField>
                <FormLabel htmlFor="profile-confirm-pw" required>
                  {t("auth.confirmPassword", "Confirm New Password")}
                </FormLabel>
                <Input
                  id="profile-confirm-pw"
                  type="password"
                  placeholder="••••••••"
                  disabled={pwForm.formState.isSubmitting}
                  {...pwForm.register("confirm_password")}
                />
                {pwForm.formState.errors.confirm_password && (
                  <p className="mt-1 text-xs text-danger">{t(pwForm.formState.errors.confirm_password.message ?? "")}</p>
                )}
              </FormField>

              <Button type="submit" disabled={pwForm.formState.isSubmitting}>
                {pwForm.formState.isSubmitting ? t("common.loading", "Updating...") : t("profile.updatePasswordBtn", "Update Password")}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* 2FA Security Notice Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            {t("profile.twoFactorSecurity", "Two-Factor Authentication (2FA / TOTP)")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-ink-muted">
            {t(
              "profile.twoFactorStatusText",
              "Two-factor authentication adds an extra layer of protection to your account using TOTP authenticator apps. 2FA setup is managed by your system administrator.",
            )}
          </p>
          <div className="flex items-center gap-2 pt-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-surface border border-border px-2.5 py-1 text-xs font-medium text-ink">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              {t("profile.standardSecurityActive", "Standard JWT Bearer Security Active")}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Active Sessions Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Laptop className="h-4 w-4 text-primary" />
              {t("profile.activeSessions", "Active Login Sessions")}
            </CardTitle>
            <p className="mt-0.5 text-xs text-ink-muted">
              {t("profile.sessionsSubtitle", "Review and revoke active devices that have logged into your account.")}
            </p>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowLogoutAllConfirm(true)}
            disabled={sessions.length === 0}
            className="text-xs"
          >
            <LogOut className="h-3.5 w-3.5 mr-1" />
            {t("profile.logoutAllSessions", "Terminate All Other Sessions")}
          </Button>
        </CardHeader>
        <CardContent>
          {loadingSessions ? (
            <p className="text-xs text-ink-muted">{t("common.loading", "Loading sessions...")}</p>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-ink-muted">{t("profile.noOtherSessions", "No other active sessions recorded.")}</p>
          ) : (
            <div className="divide-y divide-border">
              {sessions.map((sess) => (
                <div key={sess.id} className="flex items-center justify-between py-2.5 text-xs">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-canvas text-ink-muted">
                      {sess.platform === "android" || sess.platform === "ios" ? (
                        <Smartphone className="h-4 w-4" />
                      ) : (
                        <Laptop className="h-4 w-4" />
                      )}
                    </div>
                    <div>
                      <p className="font-semibold text-ink">
                        {sess.device_name || sess.platform || "Web Browser"}
                        {sess.is_active && (
                          <span className="ml-2 inline-flex items-center rounded bg-emerald-500/10 px-1.5 py-0.2 text-[10px] font-semibold text-emerald-600">
                            {t("profile.currentSession", "Active")}
                          </span>
                        )}
                      </p>
                      <p className="text-[11px] text-ink-muted font-mono">
                        {sess.ip_address} • {sess.last_activity ? `${formatDate(sess.last_activity, i18n.language)} ${formatTimeShort(new Date(sess.last_activity), i18n.language)}` : "—"}
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSessionToRevoke(sess.id)}
                    className="text-xs text-danger hover:text-danger"
                  >
                    {t("profile.revokeSession", "Revoke")}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirm Revoke Session Dialog */}
      <ConfirmDialog
        open={Boolean(sessionToRevoke)}
        onOpenChange={(open) => { if (!open) setSessionToRevoke(null); }}
        title={t("profile.revokeConfirmTitle", "Terminate Session?")}
        description={t("profile.revokeConfirmDesc", "This device will be logged out immediately and will require signing in again.")}
        impactSummary={t("profile.revokeConfirmImpact", "The refresh token for that device will be blacklisted.")}
        confirmLabel={t("profile.revokeButton", "Terminate Session")}
        destructive
        onConfirm={() => void handleRevokeSession()}
      />

      {/* Confirm Logout All Dialog */}
      <ConfirmDialog
        open={showLogoutAllConfirm}
        onOpenChange={setShowLogoutAllConfirm}
        title={t("profile.logoutAllConfirmTitle", "Terminate All Active Sessions?")}
        description={t("profile.logoutAllConfirmDesc", "All other web and mobile sessions for your account will be revoked immediately.")}
        impactSummary={t("profile.logoutAllConfirmImpact", "You will remain signed in only on your current device.")}
        confirmLabel={t("profile.logoutAllButton", "Terminate All")}
        destructive
        onConfirm={() => void handleLogoutAll()}
      />
    </div>
  );
}
