import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/query-client";
import { ErrorBoundary } from "@/components/composite/ErrorBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { Toaster } from "@/components/ui/toast";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/lib/theme";
import { authApi } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/store/authStore";
import { ProtectedRoute } from "@/features/auth/permissions";
import { IdleTimeoutDialog } from "@/features/auth/components/IdleTimeoutDialog";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ForceChangePasswordPage } from "@/features/auth/pages/ForceChangePasswordPage";
import { ProfilePage } from "@/features/auth/pages/ProfilePage";
import { ForbiddenPage } from "@/features/auth/pages/ForbiddenPage";
import { DashboardHomePage } from "@/features/dashboard/pages/DashboardHomePage";
import { ModulePlaceholderPage } from "@/features/dashboard/pages/ModulePlaceholderPage";
import { DesignSystemPage } from "@/features/design-system/pages/DesignSystemPage";

import { InstitutionProfilePage } from "@/features/institutions/pages/InstitutionProfilePage";
import { BranchesShiftsPage } from "@/features/institutions/pages/BranchesShiftsPage";
import { SessionsTermsPage } from "@/features/institutions/pages/SessionsTermsPage";
import { HolidaysPage } from "@/features/institutions/pages/HolidaysPage";
import { ClassesSectionsPage } from "@/features/academics/pages/ClassesSectionsPage";
import { SubjectsPage } from "@/features/academics/pages/SubjectsPage";
import { PeriodsRoomsPage } from "@/features/academics/pages/PeriodsRoomsPage";
import { RoutineBuilderPage } from "@/features/academics/pages/RoutineBuilderPage";
import { SubstitutesPage } from "@/features/academics/pages/SubstitutesPage";
import { CopySessionWizardPage } from "@/features/academics/pages/CopySessionWizardPage";
import { StudentsListPage } from "@/features/students/pages/StudentsListPage";
import { StudentDetailPage } from "@/features/students/pages/StudentDetailPage";
import { StudentCreatePage } from "@/features/students/pages/StudentCreatePage";
import { GuardiansListPage } from "@/features/students/pages/GuardiansListPage";
import { AdmissionsOverviewPage } from "@/features/admissions/pages/AdmissionsOverviewPage";

function SessionBootstrap({ children }: { children: React.ReactNode }) {
  const { refreshToken, setTokens, setUser, logout, setIsRestoring } = useAuthStore();

  useEffect(() => {
    let isCancelled = false;

    async function restoreSession() {
      if (!refreshToken) {
        setIsRestoring(false);
        return;
      }

      try {
        const refreshData = await authApi.refresh(refreshToken);
        if (isCancelled) return;
        setTokens(refreshData.access, refreshData.refresh);

        const me = await authApi.getMe();
        if (isCancelled) return;
        setUser(me as never);
      } catch {
        if (!isCancelled) {
          logout();
        }
      } finally {
        if (!isCancelled) {
          setIsRestoring(false);
        }
      }
    }

    void restoreSession();

    return () => {
      isCancelled = true;
    };
  }, [refreshToken, setTokens, setUser, logout, setIsRestoring]);

  return <>{children}</>;
}

export function AppRoutes() {
  const { isAuthenticated, refreshToken, logout, user } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    if (refreshToken) {
      void authApi.logout(refreshToken).catch(() => {
        // Ignore network error on logout
      });
    }
    logout();
    void navigate("/login");
  };

  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
        }
      />
      <Route
        path="/forgot-password"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <ForgotPasswordPage />
        }
      />
      <Route path="/403" element={<ForbiddenPage />} />

      {/* Force Change Password */}
      <Route
        path="/force-change-password"
        element={
          <ProtectedRoute>
            <ForceChangePasswordPage />
          </ProtectedRoute>
        }
      />

      {/* Protected App Routes inside AppShell */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppShell permissions={user?.permissions} onLogout={handleLogout}>
              <Routes>
                <Route path="/" element={<DashboardHomePage />} />
                <Route path="/profile" element={<ProfilePage />} />

                {/* Institution Routes */}
                <Route
                  path="/institution/profile"
                  element={
                    <ProtectedRoute perm="institutions.view">
                      <InstitutionProfilePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/institution/branches"
                  element={
                    <ProtectedRoute perm="institutions.view">
                      <BranchesShiftsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/institution/sessions"
                  element={
                    <ProtectedRoute perm="institutions.view">
                      <SessionsTermsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/institution/holidays"
                  element={
                    <ProtectedRoute perm="institutions.view">
                      <HolidaysPage />
                    </ProtectedRoute>
                  }
                />

                {/* Academics Routes */}
                <Route
                  path="/academics/classes"
                  element={
                    <ProtectedRoute perm="academics.view">
                      <ClassesSectionsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/academics/subjects"
                  element={
                    <ProtectedRoute perm="academics.view">
                      <SubjectsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/academics/periods"
                  element={
                    <ProtectedRoute perm="academics.view">
                      <PeriodsRoomsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/academics/routine"
                  element={
                    <ProtectedRoute perm="academics.view">
                      <RoutineBuilderPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/academics/substitutes"
                  element={
                    <ProtectedRoute perm="academics.view">
                      <SubstitutesPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/academics/copy-session"
                  element={
                    <ProtectedRoute perm="academics.manage">
                      <CopySessionWizardPage />
                    </ProtectedRoute>
                  }
                />

                {/* Students Routes */}
                <Route
                  path="/students"
                  element={
                    <ProtectedRoute perm="students.view">
                      <StudentsListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/students/new"
                  element={
                    <ProtectedRoute perm="students.manage">
                      <StudentCreatePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/students/guardians"
                  element={
                    <ProtectedRoute perm="students.view">
                      <GuardiansListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/students/:id"
                  element={
                    <ProtectedRoute perm="students.view">
                      <StudentDetailPage />
                    </ProtectedRoute>
                  }
                />

                {/* Admissions Routes */}
                <Route
                  path="/admissions"
                  element={
                    <ProtectedRoute perm="admissions.view">
                      <AdmissionsOverviewPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/attendance"
                  element={
                    <ProtectedRoute perm="attendance.view">
                      <ModulePlaceholderPage titleKey="nav.attendance" />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/exams"
                  element={
                    <ProtectedRoute perm="exams.view">
                      <ModulePlaceholderPage titleKey="nav.exams" />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <ModulePlaceholderPage titleKey="nav.fees" />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/staff"
                  element={
                    <ProtectedRoute perm="staff.view">
                      <ModulePlaceholderPage titleKey="nav.staff" />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/devices"
                  element={
                    <ProtectedRoute perm="devices.view">
                      <ModulePlaceholderPage titleKey="nav.devices" />
                    </ProtectedRoute>
                  }
                />
                <Route path="/system" element={<DashboardHomePage />} />
                {import.meta.env.DEV ? (
                  <Route path="/_design" element={<DesignSystemPage />} />
                ) : null}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <QueryClientProvider client={queryClient}>
          <ErrorBoundary>
            <BrowserRouter basename="/dashboard">
              <SessionBootstrap>
                <AppRoutes />
                <IdleTimeoutDialog />
              </SessionBootstrap>
            </BrowserRouter>
            <Toaster />
          </ErrorBoundary>
        </QueryClientProvider>
      </TooltipProvider>
    </ThemeProvider>
  );
}

export default App;
