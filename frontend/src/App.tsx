import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "@/components/composite/ErrorBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { Toaster } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { DashboardHomePage } from "@/features/dashboard/pages/DashboardHomePage";
import { ModulePlaceholderPage } from "@/features/dashboard/pages/ModulePlaceholderPage";
import { DesignSystemPage } from "@/features/design-system/pages/DesignSystemPage";
import { ThemeProvider } from "@/lib/theme";

const AUTH_SESSION_KEY = "sms_dashboard_authenticated";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

interface AppRoutesProps {
  isAuthenticated?: boolean;
  onLoginSuccess?: () => void;
  onLogout?: () => void;
}

export function AppRoutes({
  isAuthenticated: isAuthenticatedProp,
  onLoginSuccess,
  onLogout,
}: AppRoutesProps) {
  const [localAuth, setLocalAuth] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(AUTH_SESSION_KEY) === "true";
  });

  const authenticated = isAuthenticatedProp ?? localAuth;

  const handleLogin = () => {
    window.localStorage.setItem(AUTH_SESSION_KEY, "true");
    setLocalAuth(true);
    onLoginSuccess?.();
  };

  const handleLogout = () => {
    window.localStorage.removeItem(AUTH_SESSION_KEY);
    setLocalAuth(false);
    onLogout?.();
  };

  if (!authenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLoginSuccess={handleLogin} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <AppShell onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<DashboardHomePage />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/students" element={<ModulePlaceholderPage titleKey="nav.students" />} />
        <Route path="/attendance" element={<ModulePlaceholderPage titleKey="nav.attendance" />} />
        <Route path="/exams" element={<ModulePlaceholderPage titleKey="nav.exams" />} />
        <Route path="/fees" element={<ModulePlaceholderPage titleKey="nav.fees" />} />
        <Route path="/staff" element={<ModulePlaceholderPage titleKey="nav.staff" />} />
        <Route path="/devices" element={<ModulePlaceholderPage titleKey="nav.devices" />} />
        <Route path="/system" element={<DashboardHomePage />} />
        {import.meta.env.DEV ? <Route path="/_design" element={<DesignSystemPage />} /> : null}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <QueryClientProvider client={queryClient}>
          <ErrorBoundary>
            <BrowserRouter basename="/dashboard">
              <AppRoutes />
            </BrowserRouter>
            <Toaster />
          </ErrorBoundary>
        </QueryClientProvider>
      </TooltipProvider>
    </ThemeProvider>
  );
}

export default App;
