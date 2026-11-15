import { useEffect, useRef } from "react";
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
import StaffListPage from "@/features/staff/pages/StaffListPage";
import StaffCreatePage from "@/features/staff/pages/StaffCreatePage";
import StaffDetailPage from "@/features/staff/pages/StaffDetailPage";
import DepartmentsDesignationsPage from "@/features/staff/pages/DepartmentsDesignationsPage";
import LeaveManagementPage from "@/features/staff/pages/LeaveManagementPage";
import DeviceListPage from "@/features/devices/pages/DeviceListPage";
import DailyAttendancePage from "@/features/attendance/pages/DailyAttendancePage";
import AttendanceCorrectionsPage from "@/features/attendance/pages/AttendanceCorrectionsPage";
import PeriodAttendancePage from "@/features/attendance/pages/PeriodAttendancePage";
import AttendancePoliciesPage from "@/features/attendance/pages/AttendancePoliciesPage";
import ExamListPage from "@/features/exams/pages/ExamListPage";
import ExamDetailPage from "@/features/exams/pages/ExamDetailPage";
import MarkEntryPage from "@/features/exams/pages/MarkEntryPage";
import AdmitCardsPage from "@/features/exams/pages/AdmitCardsPage";
import ResultsDashboardPage from "@/features/results/pages/ResultsDashboardPage";
import TabulationSheetPage from "@/features/results/pages/TabulationSheetPage";
import ReportCardsPage from "@/features/results/pages/ReportCardsPage";
import GradingScalesPage from "@/features/results/pages/GradingScalesPage";

function SessionBootstrap({ children }: { children: React.ReactNode }) {
  const { setTokens, setUser, logout, setIsRestoring } = useAuthStore();
  const hasBootstrapped = useRef(false);

  useEffect(() => {
    if (hasBootstrapped.current) return;
    hasBootstrapped.current = true;

    async function restoreSession() {
      const { refreshToken, accessToken } = useAuthStore.getState();
      if (!refreshToken) {
        setIsRestoring(false);
        return;
      }

      try {
        // If access token is missing, refresh tokens first
        if (!accessToken) {
          const refreshData = await authApi.refresh(refreshToken);
          setTokens(refreshData.access, refreshData.refresh);
        }

        // Background sync to verify session validity and refresh user profile & permissions
        const me = await authApi.getMe();
        setUser(me as never);
      } catch {
        // Token refresh or profile fetch failed (token expired/blacklisted)
        // Only log out if we don't even have a valid session
        logout();
      } finally {
        setIsRestoring(false);
      }
    }

    void restoreSession();
  }, [setTokens, setUser, logout, setIsRestoring]);

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
            <AppShell permissions={user?.permissions} userType={user?.user_type} onLogout={handleLogout}>
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
                {/* Attendance Routes */}
                <Route
                  path="/attendance"
                  element={
                    <ProtectedRoute perm="attendance.view">
                      <DailyAttendancePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/attendance/corrections"
                  element={
                    <ProtectedRoute perm="attendance.view">
                      <AttendanceCorrectionsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/attendance/periods"
                  element={
                    <ProtectedRoute perm="attendance.view">
                      <PeriodAttendancePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/attendance/policies"
                  element={
                    <ProtectedRoute perm="attendance.view">
                      <AttendancePoliciesPage />
                    </ProtectedRoute>
                  }
                />
                {/* Examination Routes */}
                <Route
                  path="/exams"
                  element={
                    <ProtectedRoute perm="exams.view">
                      <ExamListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/exams/marks"
                  element={
                    <ProtectedRoute perm="exams.view">
                      <MarkEntryPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/exams/admit-cards"
                  element={
                    <ProtectedRoute perm="exams.view">
                      <AdmitCardsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/exams/:id"
                  element={
                    <ProtectedRoute perm="exams.view">
                      <ExamDetailPage />
                    </ProtectedRoute>
                  }
                />

                {/* Results & Tabulation Routes */}
                <Route
                  path="/results"
                  element={
                    <ProtectedRoute perm="results.view">
                      <ResultsDashboardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/results/tabulation"
                  element={
                    <ProtectedRoute perm="results.view">
                      <TabulationSheetPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/results/report-cards"
                  element={
                    <ProtectedRoute perm="results.view">
                      <ReportCardsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/results/grading-scales"
                  element={
                    <ProtectedRoute perm="results.view">
                      <GradingScalesPage />
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
                {/* Staff & HR Routes */}
                <Route
                  path="/staff"
                  element={
                    <ProtectedRoute perm="staff.view">
                      <StaffListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/staff/new"
                  element={
                    <ProtectedRoute perm="staff.manage">
                      <StaffCreatePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/staff/departments"
                  element={
                    <ProtectedRoute perm="staff.view">
                      <DepartmentsDesignationsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/staff/leaves"
                  element={
                    <ProtectedRoute perm="staff.view">
                      <LeaveManagementPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/staff/:id"
                  element={
                    <ProtectedRoute perm="staff.view">
                      <StaffDetailPage />
                    </ProtectedRoute>
                  }
                />
                {/* Devices Routes */}
                <Route
                  path="/devices"
                  element={
                    <ProtectedRoute perm="devices.view">
                      <DeviceListPage />
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
