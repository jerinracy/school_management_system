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
    | "staff"
    | "devices"
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
    to: "/fees",
    labelKey: "nav.fees",
    iconName: "fees",
    permission: "fees.view",
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
    id: "system",
    to: "/system",
    labelKey: "nav.settings",
    iconName: "system",
    permission: "system.view",
  },
];
