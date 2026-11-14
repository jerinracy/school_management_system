import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { useAuthStore } from "@/features/auth/store/authStore";

// Default idle timeout: 20 minutes warning, auto-logout after 60 seconds
const IDLE_TIMEOUT_MS = 20 * 60 * 1000;
const WARNING_DURATION_SECONDS = 60;

export function IdleTimeoutDialog() {
  const { t } = useTranslation();
  const { isAuthenticated, logout } = useAuthStore();
  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(WARNING_DURATION_SECONDS);

  useEffect(() => {
    if (!isAuthenticated) return;

    let idleTimer: ReturnType<typeof setTimeout> | undefined;

    const resetIdleTimer = () => {
      if (idleTimer) clearTimeout(idleTimer);
      if (!showWarning) {
        idleTimer = setTimeout(() => {
          setShowWarning(true);
          setCountdown(WARNING_DURATION_SECONDS);
        }, IDLE_TIMEOUT_MS);
      }
    };

    const handleActivity = () => {
      if (!showWarning) {
        resetIdleTimer();
      }
    };

    window.addEventListener("mousemove", handleActivity);
    window.addEventListener("keydown", handleActivity);
    window.addEventListener("click", handleActivity);
    window.addEventListener("touchstart", handleActivity);

    resetIdleTimer();

    return () => {
      if (idleTimer) clearTimeout(idleTimer);
      window.removeEventListener("mousemove", handleActivity);
      window.removeEventListener("keydown", handleActivity);
      window.removeEventListener("click", handleActivity);
      window.removeEventListener("touchstart", handleActivity);
    };
  }, [isAuthenticated, showWarning]);

  useEffect(() => {
    if (!showWarning) return;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setShowWarning(false);
          logout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [showWarning, logout]);

  const handleExtend = () => {
    setShowWarning(false);
    setCountdown(WARNING_DURATION_SECONDS);
  };

  return (
    <ConfirmDialog
      open={showWarning}
      onOpenChange={(open) => {
        if (!open) handleExtend();
      }}
      title={t("auth.idleWarningTitle", "Idle Session Warning")}
      description={t(
        "auth.idleWarningDesc",
        "You have been inactive for a while. For your security, you will be logged out automatically in {{seconds}} seconds.",
        { seconds: countdown },
      )}
      impactSummary={t("auth.idleWarningImpact", "Click 'Stay Logged In' to keep your current work.")}
      confirmLabel={t("auth.stayLoggedIn", "Stay Logged In")}
      cancelLabel={t("auth.logoutNow", "Log Out Now")}
      onConfirm={handleExtend}
    />
  );
}
