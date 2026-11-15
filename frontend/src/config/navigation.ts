export interface NavSubItemConfig {
  id: string;
  to: string;
  labelKey: string;
  permission?: string;
  end?: boolean;
}

export interface NavItemConfig {
  id: string;
  to: string;
  labelKey: string;
  iconName:
    | "overview"
    | "institution"
    | "academics"
    | "students"
    | "admissions"
    | "attendance"
    | "exams"
    | "results"
    | "fees"
    | "accounting"
    | "payroll"
    | "staff"
    | "devices"
    | "communications"
    | "calendar"
    | "operations"
    | "system";
  end?: boolean;
  permission?: string;
  children?: NavSubItemConfig[];
}

export const SIDEBAR_NAV_ITEMS: NavItemConfig[] = [
  { id: "overview", to: "/", labelKey: "nav.overview", iconName: "overview", end: true },
  {
    id: "institution",
    to: "/institution/profile",
    labelKey: "nav.institution",
    iconName: "institution",
    permission: "institutions.view",
    children: [
      { id: "inst-profile", to: "/institution/profile", labelKey: "nav.institutionProfile", end: true },
      { id: "inst-branches", to: "/institution/branches", labelKey: "nav.branchesShifts" },
      { id: "inst-sessions", to: "/institution/sessions", labelKey: "nav.sessionsTerms" },
      { id: "inst-holidays", to: "/institution/holidays", labelKey: "nav.academicHolidays" },
    ],
  },
  {
    id: "academics",
    to: "/academics/classes",
    labelKey: "nav.academics",
    iconName: "academics",
    permission: "academics.view",
    children: [
      { id: "acad-classes", to: "/academics/classes", labelKey: "nav.classesSections" },
      { id: "acad-subjects", to: "/academics/subjects", labelKey: "nav.subjects" },
      { id: "acad-periods", to: "/academics/periods", labelKey: "nav.periodsRooms" },
      { id: "acad-routine", to: "/academics/routine", labelKey: "nav.classRoutine" },
      { id: "acad-substitutes", to: "/academics/substitutes", labelKey: "nav.teacherSubstitutes" },
      { id: "acad-copy", to: "/academics/copy-session", labelKey: "nav.copySession", permission: "academics.manage" },
    ],
  },
  {
    id: "students",
    to: "/students",
    labelKey: "nav.students",
    iconName: "students",
    permission: "students.view",
    children: [
      { id: "stud-directory", to: "/students", labelKey: "nav.studentDirectory", end: true },
      { id: "stud-new", to: "/students/new", labelKey: "nav.enrollStudent", permission: "students.manage" },
      { id: "stud-guardians", to: "/students/guardians", labelKey: "nav.guardiansDirectory" },
    ],
  },
  {
    id: "admissions",
    to: "/admissions",
    labelKey: "nav.admissions",
    iconName: "admissions",
    permission: "admissions.view",
  },
  {
    id: "attendance",
    to: "/attendance",
    labelKey: "nav.attendance",
    iconName: "attendance",
    permission: "attendance.view",
    children: [
      { id: "att-daily", to: "/attendance", labelKey: "nav.dailyAttendance", end: true },
      { id: "att-periods", to: "/attendance/periods", labelKey: "nav.periodAttendance" },
      { id: "att-corrections", to: "/attendance/corrections", labelKey: "nav.attendanceCorrections" },
      { id: "att-policies", to: "/attendance/policies", labelKey: "nav.attendancePolicies" },
    ],
  },
  {
    id: "exams",
    to: "/exams",
    labelKey: "nav.exams",
    iconName: "exams",
    permission: "exams.view",
    children: [
      { id: "exams-list", to: "/exams", labelKey: "nav.examsList", end: true },
      { id: "exams-marks", to: "/exams/marks", labelKey: "nav.markEntry" },
      { id: "exams-admit", to: "/exams/admit-cards", labelKey: "nav.admitCards" },
    ],
  },
  {
    id: "results",
    to: "/results",
    labelKey: "nav.results",
    iconName: "results",
    permission: "results.view",
    children: [
      { id: "res-dashboard", to: "/results", labelKey: "nav.resultsDashboard", end: true },
      { id: "res-tabulation", to: "/results/tabulation", labelKey: "nav.tabulationSheet" },
      { id: "res-report-cards", to: "/results/report-cards", labelKey: "nav.reportCards" },
      { id: "res-scales", to: "/results/grading-scales", labelKey: "nav.gradingScales" },
    ],
  },
  {
    id: "fees",
    to: "/fees/invoices",
    labelKey: "nav.fees",
    iconName: "fees",
    permission: "fees.view",
    children: [
      { id: "fees-invoices", to: "/fees/invoices", labelKey: "nav.invoicesList" },
      { id: "fees-collect", to: "/fees/collect", labelKey: "nav.counterCollect" },
      { id: "fees-receipts", to: "/fees/receipts", labelKey: "nav.moneyReceipts" },
      { id: "fees-structures", to: "/fees/structures", labelKey: "nav.feeStructures" },
      { id: "fees-waivers", to: "/fees/waivers", labelKey: "nav.waivers" },
      { id: "fees-due-list", to: "/fees/due-list", labelKey: "nav.dueList" },
    ],
  },
  {
    id: "accounting",
    to: "/accounting/cashbook",
    labelKey: "nav.accounting",
    iconName: "accounting",
    permission: "accounting.view",
    children: [
      { id: "acc-cashbook", to: "/accounting/cashbook", labelKey: "nav.cashbook" },
    ],
  },
  {
    id: "payroll",
    to: "/payroll/runs",
    labelKey: "nav.payroll",
    iconName: "payroll",
    permission: "payroll.view",
    children: [
      { id: "payroll-runs", to: "/payroll/runs", labelKey: "nav.payrollRuns" },
      { id: "payroll-profiles", to: "/payroll/profiles", labelKey: "nav.salaryProfiles" },
      { id: "payroll-structures", to: "/payroll/structures", labelKey: "nav.salaryStructures" },
      { id: "payroll-loans", to: "/payroll/loans", labelKey: "nav.staffLoans" },
      { id: "payroll-payslips", to: "/payroll/payslips", labelKey: "nav.payslipsArchive" },
    ],
  },
  {
    id: "staff",
    to: "/staff",
    labelKey: "nav.staff",
    iconName: "staff",
    permission: "staff.view",
    children: [
      { id: "staff-directory", to: "/staff", labelKey: "nav.staffDirectory", end: true },
      { id: "staff-new", to: "/staff/new", labelKey: "nav.onboardStaff", permission: "staff.manage" },
    ],
  },
  {
    id: "devices",
    to: "/devices",
    labelKey: "nav.devices",
    iconName: "devices",
    permission: "devices.view",
  },
  {
    id: "communications",
    to: "/communications/sms",
    labelKey: "nav.communications",
    iconName: "communications",
    permission: "communications.view",
    children: [
      { id: "comm-sms", to: "/communications/sms", labelKey: "nav.smsGateway" },
      { id: "comm-notices", to: "/communications/notices", labelKey: "nav.noticeBoard" },
      { id: "comm-templates", to: "/communications/templates", labelKey: "nav.messageTemplates" },
      { id: "comm-deliveries", to: "/communications/deliveries", labelKey: "nav.deliveryLogs" },
      { id: "comm-emergency", to: "/communications/emergency", labelKey: "nav.emergencyAlerts" },
    ],
  },
  {
    id: "calendar",
    to: "/events/calendar",
    labelKey: "nav.calendar",
    iconName: "calendar",
    permission: "events.view",
  },
  {
    id: "operations",
    to: "/operations/homework",
    labelKey: "nav.operations",
    iconName: "operations",
    permission: "homework.view",
    children: [
      { id: "ops-homework", to: "/operations/homework", labelKey: "nav.homework" },
      { id: "ops-library", to: "/operations/library/books", labelKey: "nav.libraryCatalog" },
      { id: "ops-circulation", to: "/operations/library/circulation", labelKey: "nav.libraryCirculation" },
      { id: "ops-transport", to: "/operations/transport/vehicles", labelKey: "nav.transportFleet" },
      { id: "ops-routes", to: "/operations/transport/routes", labelKey: "nav.transportRoutes" },
      { id: "ops-hostel", to: "/operations/hostel/rooms", labelKey: "nav.hostelDorms" },
      { id: "ops-allocations", to: "/operations/hostel/allocations", labelKey: "nav.hostelAllocations" },
    ],
  },
  {
    id: "system",
    to: "/system",
    labelKey: "nav.settings",
    iconName: "system",
    permission: "system.view",
  },
];
