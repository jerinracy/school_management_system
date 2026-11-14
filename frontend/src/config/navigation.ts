export interface NavItemConfig {
  id: string;
  to: string;
  labelKey: string;
  iconName:
    | "overview"
    | "institution"
    | "academics"
    | "students"
    | "attendance"
    | "exams"
    | "fees"
    | "staff"
    | "devices"
    | "system";
  end?: boolean;
  permission?: string;
}

export const SIDEBAR_NAV_ITEMS: NavItemConfig[] = [
  { id: "overview", to: "/", labelKey: "nav.overview", iconName: "overview", end: true },
  {
    id: "institution",
    to: "/institution/profile",
    labelKey: "nav.institution",
    iconName: "institution",
    permission: "institutions.view",
  },
  {
    id: "academics",
    to: "/academics/classes",
    labelKey: "nav.academics",
    iconName: "academics",
    permission: "academics.view",
  },
  {
    id: "students",
    to: "/students",
    labelKey: "nav.students",
    iconName: "students",
    permission: "students.view",
  },
  {
    id: "attendance",
    to: "/attendance",
    labelKey: "nav.attendance",
    iconName: "attendance",
    permission: "attendance.view",
  },
  {
    id: "exams",
    to: "/exams",
    labelKey: "nav.exams",
    iconName: "exams",
    permission: "exams.view",
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
