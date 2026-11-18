import { lazy, Suspense, useEffect, useRef } from "react";
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

// Core initial pages loaded eagerly for instant startup
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ForceChangePasswordPage } from "@/features/auth/pages/ForceChangePasswordPage";
import { ProfilePage } from "@/features/auth/pages/ProfilePage";
import { ForbiddenPage } from "@/features/auth/pages/ForbiddenPage";
import { DashboardHomePage } from "@/features/dashboard/pages/DashboardHomePage";

// Secondary feature pages loaded on-demand via React.lazy()
const DesignSystemPage = lazy(() => import("@/features/design-system/pages/DesignSystemPage").then((m) => ({ default: m.DesignSystemPage })));

const InstitutionProfilePage = lazy(() => import("@/features/institutions/pages/InstitutionProfilePage").then((m) => ({ default: m.InstitutionProfilePage })));
const BranchesShiftsPage = lazy(() => import("@/features/institutions/pages/BranchesShiftsPage").then((m) => ({ default: m.BranchesShiftsPage })));
const SessionsTermsPage = lazy(() => import("@/features/institutions/pages/SessionsTermsPage").then((m) => ({ default: m.SessionsTermsPage })));
const HolidaysPage = lazy(() => import("@/features/institutions/pages/HolidaysPage").then((m) => ({ default: m.HolidaysPage })));

const ClassesSectionsPage = lazy(() => import("@/features/academics/pages/ClassesSectionsPage").then((m) => ({ default: m.ClassesSectionsPage })));
const SubjectsPage = lazy(() => import("@/features/academics/pages/SubjectsPage").then((m) => ({ default: m.SubjectsPage })));
const PeriodsRoomsPage = lazy(() => import("@/features/academics/pages/PeriodsRoomsPage").then((m) => ({ default: m.PeriodsRoomsPage })));
const RoutineBuilderPage = lazy(() => import("@/features/academics/pages/RoutineBuilderPage").then((m) => ({ default: m.RoutineBuilderPage })));
const SubstitutesPage = lazy(() => import("@/features/academics/pages/SubstitutesPage").then((m) => ({ default: m.SubstitutesPage })));
const CopySessionWizardPage = lazy(() => import("@/features/academics/pages/CopySessionWizardPage").then((m) => ({ default: m.CopySessionWizardPage })));

const StudentsListPage = lazy(() => import("@/features/students/pages/StudentsListPage").then((m) => ({ default: m.StudentsListPage })));
const StudentDetailPage = lazy(() => import("@/features/students/pages/StudentDetailPage").then((m) => ({ default: m.StudentDetailPage })));
const StudentCreatePage = lazy(() => import("@/features/students/pages/StudentCreatePage").then((m) => ({ default: m.StudentCreatePage })));
const GuardiansListPage = lazy(() => import("@/features/students/pages/GuardiansListPage").then((m) => ({ default: m.GuardiansListPage })));
const AdmissionsOverviewPage = lazy(() => import("@/features/admissions/pages/AdmissionsOverviewPage").then((m) => ({ default: m.AdmissionsOverviewPage })));

const StaffListPage = lazy(() => import("@/features/staff/pages/StaffListPage"));
const StaffCreatePage = lazy(() => import("@/features/staff/pages/StaffCreatePage"));
const StaffDetailPage = lazy(() => import("@/features/staff/pages/StaffDetailPage"));
const DepartmentsDesignationsPage = lazy(() => import("@/features/staff/pages/DepartmentsDesignationsPage"));
const LeaveManagementPage = lazy(() => import("@/features/staff/pages/LeaveManagementPage"));

const DeviceListPage = lazy(() => import("@/features/devices/pages/DeviceListPage"));
const DailyAttendancePage = lazy(() => import("@/features/attendance/pages/DailyAttendancePage"));
const AttendanceCorrectionsPage = lazy(() => import("@/features/attendance/pages/AttendanceCorrectionsPage"));
const PeriodAttendancePage = lazy(() => import("@/features/attendance/pages/PeriodAttendancePage"));
const AttendancePoliciesPage = lazy(() => import("@/features/attendance/pages/AttendancePoliciesPage"));

const ExamListPage = lazy(() => import("@/features/exams/pages/ExamListPage"));
const ExamDetailPage = lazy(() => import("@/features/exams/pages/ExamDetailPage"));
const MarkEntryPage = lazy(() => import("@/features/exams/pages/MarkEntryPage"));
const AdmitCardsPage = lazy(() => import("@/features/exams/pages/AdmitCardsPage"));
const ResultsDashboardPage = lazy(() => import("@/features/results/pages/ResultsDashboardPage"));
const TabulationSheetPage = lazy(() => import("@/features/results/pages/TabulationSheetPage"));
const ReportCardsPage = lazy(() => import("@/features/results/pages/ReportCardsPage"));
const GradingScalesPage = lazy(() => import("@/features/results/pages/GradingScalesPage"));

const InvoicesListPage = lazy(() => import("@/features/fees/pages/InvoicesListPage"));
const InvoiceDetailPage = lazy(() => import("@/features/fees/pages/InvoiceDetailPage"));
const CounterCollectionPage = lazy(() => import("@/features/fees/pages/CounterCollectionPage"));
const MoneyReceiptsPage = lazy(() => import("@/features/fees/pages/MoneyReceiptsPage"));
const FeeStructuresPage = lazy(() => import("@/features/fees/pages/FeeStructuresPage"));
const WaiversPage = lazy(() => import("@/features/fees/pages/WaiversPage"));
const DueListPage = lazy(() => import("@/features/fees/pages/DueListPage"));
const CashbookPage = lazy(() => import("@/features/accounting/pages/CashbookPage"));

const PayrollRunsListPage = lazy(() => import("@/features/payroll/pages/PayrollRunsListPage"));
const PayrollRunDetailPage = lazy(() => import("@/features/payroll/pages/PayrollRunDetailPage"));
const SalaryProfilesPage = lazy(() => import("@/features/payroll/pages/SalaryProfilesPage"));
const SalaryStructuresPage = lazy(() => import("@/features/payroll/pages/SalaryStructuresPage"));
const StaffLoansPage = lazy(() => import("@/features/payroll/pages/StaffLoansPage"));
const PayslipsListPage = lazy(() => import("@/features/payroll/pages/PayslipsListPage"));

const SMSCampaignPage = lazy(() => import("@/features/communications/pages/SMSCampaignPage").then((m) => ({ default: m.SMSCampaignPage })));
const NoticeBoardPage = lazy(() => import("@/features/communications/pages/NoticeBoardPage").then((m) => ({ default: m.NoticeBoardPage })));
const TemplatesPage = lazy(() => import("@/features/communications/pages/TemplatesPage").then((m) => ({ default: m.TemplatesPage })));
const DeliveryLogsPage = lazy(() => import("@/features/communications/pages/DeliveryLogsPage").then((m) => ({ default: m.DeliveryLogsPage })));
const EmergencyAlertsPage = lazy(() => import("@/features/communications/pages/EmergencyAlertsPage").then((m) => ({ default: m.EmergencyAlertsPage })));
const UnifiedCalendarPage = lazy(() => import("@/features/events/pages/UnifiedCalendarPage").then((m) => ({ default: m.UnifiedCalendarPage })));

const HomeworkListPage = lazy(() => import("@/features/operations/pages/HomeworkListPage").then((m) => ({ default: m.HomeworkListPage })));
const HomeworkSubmissionsPage = lazy(() => import("@/features/operations/pages/HomeworkSubmissionsPage").then((m) => ({ default: m.HomeworkSubmissionsPage })));
const LibraryCatalogPage = lazy(() => import("@/features/operations/pages/LibraryCatalogPage").then((m) => ({ default: m.LibraryCatalogPage })));
const LibraryCirculationPage = lazy(() => import("@/features/operations/pages/LibraryCirculationPage").then((m) => ({ default: m.LibraryCirculationPage })));
const TransportFleetPage = lazy(() => import("@/features/operations/pages/TransportFleetPage").then((m) => ({ default: m.TransportFleetPage })));
const TransportRoutesPage = lazy(() => import("@/features/operations/pages/TransportRoutesPage").then((m) => ({ default: m.TransportRoutesPage })));
const HostelDormsPage = lazy(() => import("@/features/operations/pages/HostelDormsPage").then((m) => ({ default: m.HostelDormsPage })));
const HostelAllocationsPage = lazy(() => import("@/features/operations/pages/HostelAllocationsPage").then((m) => ({ default: m.HostelAllocationsPage })));

const AuditLogsPage = lazy(() => import("@/features/reports/pages/AuditLogsPage").then((m) => ({ default: m.AuditLogsPage })));
const ActivityLogsPage = lazy(() => import("@/features/reports/pages/ActivityLogsPage").then((m) => ({ default: m.ActivityLogsPage })));
const ReportDefinitionsPage = lazy(() => import("@/features/reports/pages/ReportDefinitionsPage").then((m) => ({ default: m.ReportDefinitionsPage })));
const ReportExportsPage = lazy(() => import("@/features/reports/pages/ReportExportsPage").then((m) => ({ default: m.ReportExportsPage })));
const BulkImportsPage = lazy(() => import("@/features/reports/pages/BulkImportsPage").then((m) => ({ default: m.BulkImportsPage })));

function PageFallbackLoader() {
  return (
    <div className="flex h-[50vh] w-full items-center justify-center">
      <div className="flex flex-col items-center gap-2.5">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-[11px] text-ink-muted">Loading...</span>
      </div>
    </div>
  );
}

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
              <Suspense fallback={<PageFallbackLoader />}>
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
                {/* Fees & Billing Routes */}
                <Route
                  path="/fees"
                  element={<Navigate to="/fees/invoices" replace />}
                />
                <Route
                  path="/fees/invoices"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <InvoicesListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees/invoices/:id"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <InvoiceDetailPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees/collect"
                  element={
                    <ProtectedRoute perm="fees.change">
                      <CounterCollectionPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees/receipts"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <MoneyReceiptsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees/structures"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <FeeStructuresPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees/waivers"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <WaiversPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/fees/due-list"
                  element={
                    <ProtectedRoute perm="fees.view">
                      <DueListPage />
                    </ProtectedRoute>
                  }
                />

                {/* Accounting Routes */}
                <Route
                  path="/accounting"
                  element={<Navigate to="/accounting/cashbook" replace />}
                />
                <Route
                  path="/accounting/cashbook"
                  element={
                    <ProtectedRoute perm="accounting.view">
                      <CashbookPage />
                    </ProtectedRoute>
                  }
                />
                {/* Payroll Routes */}
                <Route
                  path="/payroll"
                  element={<Navigate to="/payroll/runs" replace />}
                />
                <Route
                  path="/payroll/runs"
                  element={
                    <ProtectedRoute perm="payroll.view">
                      <PayrollRunsListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/payroll/runs/:id"
                  element={
                    <ProtectedRoute perm="payroll.view">
                      <PayrollRunDetailPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/payroll/profiles"
                  element={
                    <ProtectedRoute perm="payroll.view">
                      <SalaryProfilesPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/payroll/structures"
                  element={
                    <ProtectedRoute perm="payroll.view">
                      <SalaryStructuresPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/payroll/loans"
                  element={
                    <ProtectedRoute perm="payroll.view">
                      <StaffLoansPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/payroll/payslips"
                  element={
                    <ProtectedRoute perm="payroll.view">
                      <PayslipsListPage />
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
                {/* Communications Routes */}
                <Route
                  path="/communications/sms"
                  element={
                    <ProtectedRoute perm="communications.view">
                      <SMSCampaignPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/communications/notices"
                  element={
                    <ProtectedRoute perm="communications.view">
                      <NoticeBoardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/communications/templates"
                  element={
                    <ProtectedRoute perm="communications.view">
                      <TemplatesPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/communications/deliveries"
                  element={
                    <ProtectedRoute perm="communications.view">
                      <DeliveryLogsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/communications/emergency"
                  element={
                    <ProtectedRoute perm="communications.view">
                      <EmergencyAlertsPage />
                    </ProtectedRoute>
                  }
                />
                {/* Events / Calendar Routes */}
                <Route
                  path="/events/calendar"
                  element={
                    <ProtectedRoute perm="events.view">
                      <UnifiedCalendarPage />
                    </ProtectedRoute>
                  }
                />
                {/* Operations & Student Services Routes */}
                <Route
                  path="/operations/homework"
                  element={
                    <ProtectedRoute perm="homework.view">
                      <HomeworkListPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/homework/:id/submissions"
                  element={
                    <ProtectedRoute perm="homework.view">
                      <HomeworkSubmissionsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/library/books"
                  element={
                    <ProtectedRoute perm="library.view">
                      <LibraryCatalogPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/library/circulation"
                  element={
                    <ProtectedRoute perm="library.view">
                      <LibraryCirculationPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/transport/vehicles"
                  element={
                    <ProtectedRoute perm="transport.view">
                      <TransportFleetPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/transport/routes"
                  element={
                    <ProtectedRoute perm="transport.view">
                      <TransportRoutesPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/hostel/rooms"
                  element={
                    <ProtectedRoute perm="hostel.view">
                      <HostelDormsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/operations/hostel/allocations"
                  element={
                    <ProtectedRoute perm="hostel.view">
                      <HostelAllocationsPage />
                    </ProtectedRoute>
                  }
                />

                {/* Reports & Audit */}
                <Route
                  path="/reports/definitions"
                  element={
                    <ProtectedRoute perm="reports.view">
                      <ReportDefinitionsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/reports/exports"
                  element={
                    <ProtectedRoute perm="reports.view">
                      <ReportExportsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/reports/imports"
                  element={
                    <ProtectedRoute perm="reports.manage">
                      <BulkImportsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/audit/logs"
                  element={
                    <ProtectedRoute perm="audit.view">
                      <AuditLogsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/audit/activities"
                  element={
                    <ProtectedRoute perm="audit.view">
                      <ActivityLogsPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/system" element={<DashboardHomePage />} />
                {import.meta.env.DEV ? (
                  <Route path="/_design" element={<DesignSystemPage />} />
                ) : null}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
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
