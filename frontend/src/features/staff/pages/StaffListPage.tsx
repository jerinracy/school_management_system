import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  ChevronDown,
  ChevronRight,
  Download,
  GraduationCap,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  UserCheck,
  UserCog,
  Users,
  Eye,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { staffApi, type StaffListItem } from "@/features/staff/api/staffApi";
import { Can } from "@/features/auth/permissions";
import { useAuthStore } from "@/features/auth/store/authStore";

type SectionKey = "ALL" | "SUPERADMIN" | "ADMIN" | "TEACHER" | "STAFF";

export function StaffListPage() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const navigate = useNavigate();

  // Auth User & Role Check
  const currentUser = useAuthStore((s) => s.user);
  const isSuperAdmin =
    currentUser?.user_type === "superadmin" ||
    currentUser?.user_type === "super_admin";

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [activeSection, setActiveSection] = useState<SectionKey>("ALL");

  // Section collapse states
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    SUPERADMIN: false,
    ADMIN: false,
    TEACHER: false,
    STAFF: false,
  });

  const toggleSectionCollapse = (key: string) => {
    setCollapsedSections((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Top KPI Summary Query (Single DB aggregate query)
  const { data: summaryData, isLoading: isSummaryLoading } = useQuery({
    queryKey: ["staff-summary"],
    queryFn: () => staffApi.getStaffSummary(),
  });

  // Departments Query for filter dropdown
  const { data: departmentsData } = useQuery({
    queryKey: ["staff-departments-list"],
    queryFn: () => staffApi.getDepartments(),
  });

  const departments = departmentsData?.results ?? [];

  // Main Staff Query
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: [
      "staff",
      {
        search: debouncedSearch,
        department: departmentFilter !== "ALL" ? departmentFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      },
    ],
    queryFn: () =>
      staffApi.getStaffList({
        search: debouncedSearch || undefined,
        department: departmentFilter !== "ALL" ? departmentFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      }),
  });

  const rawStaffList: StaffListItem[] = useMemo(() => data?.results ?? [], [data?.results]);

  // Categorize Staff into 4 distinct groups
  const superadminList = useMemo(() => {
    if (!isSuperAdmin) return [];
    return rawStaffList.filter(
      (s) => s.staff_type === "superadmin" || s.user_type === "superadmin"
    );
  }, [rawStaffList, isSuperAdmin]);

  const adminList = useMemo(() => {
    return rawStaffList.filter(
      (s) =>
        (s.staff_type === "admin" ||
          ["admin", "head_teacher", "assistant_head", "accountant", "clerk"].includes(
            s.user_type || ""
          )) &&
        s.staff_type !== "superadmin" &&
        s.user_type !== "superadmin"
    );
  }, [rawStaffList]);

  const teacherList = useMemo(() => {
    return rawStaffList.filter(
      (s) =>
        (s.staff_type === "teacher" || s.user_type === "teacher") &&
        s.staff_type !== "superadmin" &&
        s.user_type !== "superadmin" &&
        s.staff_type !== "admin"
    );
  }, [rawStaffList]);

  const supportStaffList = useMemo(() => {
    return rawStaffList.filter(
      (s) =>
        !superadminList.some((item) => item.id === s.id) &&
        !adminList.some((item) => item.id === s.id) &&
        !teacherList.some((item) => item.id === s.id)
    );
  }, [rawStaffList, superadminList, adminList, teacherList]);

  // Search Debouncing
  const handleSearchChange = (value: string) => {
    setSearch(value);
    const timeout = setTimeout(() => {
      setDebouncedSearch(value);
    }, 300);
    return () => clearTimeout(timeout);
  };

  const handleResetFilters = () => {
    setSearch("");
    setDebouncedSearch("");
    setDepartmentFilter("ALL");
    setStatusFilter("ALL");
    setActiveSection("ALL");
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
            {t("common.active", "Active")}
          </span>
        );
      case "on_leave":
        return (
          <span className="inline-flex items-center rounded-md bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 text-[11px] font-semibold text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60">
            {t("staff.onLeave", "On Leave")}
          </span>
        );
      case "suspended":
      case "resigned":
      case "terminated":
      case "retired":
        return (
          <span className="inline-flex items-center rounded-md bg-rose-50 dark:bg-rose-950/60 px-2 py-0.5 text-[11px] font-semibold text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 uppercase">
            {status}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
            {status || t("common.active", "Active")}
          </span>
        );
    }
  };

  // Render a compact table for a specific category section
  const renderStaffSection = (
    sectionId: "SUPERADMIN" | "ADMIN" | "TEACHER" | "STAFF",
    title: string,
    icon: React.ReactNode,
    members: StaffListItem[],
    themeClasses: {
      border: string;
      headerBg: string;
      badgeBg: string;
      badgeText: string;
    }
  ) => {
    const isCollapsed = collapsedSections[sectionId];

    return (
      <div
        id={`section-${sectionId.toLowerCase()}`}
        className={`rounded-xl border ${themeClasses.border} bg-white dark:bg-slate-900 shadow-2xs overflow-hidden transition-all`}
      >
        {/* Section Header */}
        <button
          type="button"
          onClick={() => toggleSectionCollapse(sectionId)}
          className={`w-full text-left flex items-center justify-between px-4 py-2.5 cursor-pointer select-none ${themeClasses.headerBg} border-b ${themeClasses.border}`}
        >
          <div className="flex items-center gap-2.5">
            <span className="p-1 rounded-md bg-white/80 dark:bg-slate-800 shadow-2xs">
              {icon}
            </span>
            <div className="flex items-center gap-2">
              <h3 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100">
                {title}
              </h3>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-extrabold ${themeClasses.badgeBg} ${themeClasses.badgeText}`}
              >
                {members.length}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className="h-7 w-7 flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              aria-label={isCollapsed ? "Expand" : "Collapse"}
            >
              {isCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </span>
          </div>
        </button>

        {/* Section Table Body */}
        {!isCollapsed && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[640px]">
              <thead className="bg-slate-50/70 dark:bg-slate-800/40 border-b border-slate-200/80 dark:border-slate-800/80 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="px-3.5 py-2">{t("staff.employee", "Employee")}</th>
                  <th className="px-3.5 py-2">{t("staff.designationDept", "Designation & Dept")}</th>
                  <th className="px-3.5 py-2">{t("staff.contact", "Contact")}</th>
                  <th className="px-3.5 py-2">{t("staff.roleType", "Role & Details")}</th>
                  <th className="px-3.5 py-2">{t("common.status", "Status")}</th>
                  <th className="px-3.5 py-2 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {members.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400 text-xs">
                      {t("staff.noStaffInSection", "No employees registered in this category.")}
                    </td>
                  </tr>
                ) : (
                  members.map((member) => (
                    <tr
                      key={member.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Employee Identity */}
                      <td className="px-3.5 py-2.5">
                        <div className="flex items-center gap-2.5">
                          <div className="h-8 w-8 shrink-0 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center font-bold text-xs text-slate-700 dark:text-slate-300 overflow-hidden">
                            {member.photo ? (
                              <img
                                src={member.photo}
                                alt={member.full_name_en}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              member.full_name_en.slice(0, 2).toUpperCase()
                            )}
                          </div>
                          <div>
                            <Link
                              to={`/staff/${member.id}`}
                              className="font-bold text-xs text-slate-900 dark:text-slate-100 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors block leading-tight"
                            >
                              {currentLang === "bn" && member.full_name_bn
                                ? member.full_name_bn
                                : member.full_name_en}
                            </Link>
                            <span className="text-[10px] font-mono text-slate-400">
                              {member.employee_id}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Designation & Department */}
                      <td className="px-3.5 py-2.5">
                        <div className="space-y-0.5">
                          <span className="font-semibold text-xs text-slate-800 dark:text-slate-200 block">
                            {member.designation_title || "—"}
                          </span>
                          <span className="text-[10px] text-slate-500 block">
                            {member.department_name || "—"}
                          </span>
                        </div>
                      </td>

                      {/* Contact */}
                      <td className="px-3.5 py-2.5">
                        <div className="space-y-0.5 text-[11px]">
                          <a
                            href={`tel:${member.phone}`}
                            className="font-mono text-slate-700 dark:text-slate-300 hover:underline block"
                          >
                            {member.phone}
                          </a>
                          {member.email && (
                            <span className="text-slate-400 text-[10px] font-mono truncate block max-w-[150px]">
                              {member.email}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Role & MPO */}
                      <td className="px-3.5 py-2.5">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium capitalize text-slate-700 dark:text-slate-300">
                            {member.staff_type === "teacher" && (
                              <GraduationCap className="h-2.5 w-2.5 text-emerald-600" />
                            )}
                            {member.staff_type === "superadmin" && (
                              <ShieldCheck className="h-2.5 w-2.5 text-indigo-600" />
                            )}
                            {(member.staff_type ?? "").replace("_", " ")}
                          </span>
                          {member.is_mpo && (
                            <span className="inline-flex items-center rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/50 px-1 py-0.2 text-[9px] font-extrabold">
                              MPO
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-3.5 py-2.5">
                        {getStatusBadge(member.status)}
                      </td>

                      {/* Actions */}
                      <td className="px-3.5 py-2.5 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            void navigate(`/staff/${member.id}`);
                          }}
                          className="h-7 px-2 text-[11px] text-emerald-800 dark:text-emerald-400 hover:text-emerald-900 hover:bg-emerald-50 dark:hover:bg-emerald-950/60 rounded-md"
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          <span>{t("common.view", "View")}</span>
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-5 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("staff.directoryTitle", "Staff & Faculty Directory")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            {t(
              "staff.directorySubtitle",
              "Manage institutional employees, teachers, designations, and leave records."
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link to="/staff/departments">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs rounded-lg">
              <Briefcase className="h-3.5 w-3.5" />
              <span>{t("staff.departmentsLink", "Departments & Designations")}</span>
            </Button>
          </Link>

          <Link to="/staff/leaves">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs rounded-lg">
              <UserCheck className="h-3.5 w-3.5" />
              <span>{t("staff.leavesLink", "Leave Management")}</span>
            </Button>
          </Link>

          <a
            href={staffApi.getExportUrl()}
            download
            className="inline-flex items-center justify-center gap-1.5 h-8 px-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-2xs"
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t("common.export", "Export")}</span>
          </a>

          <Can perm="staff.manage">
            <Button
              size="sm"
              onClick={() => {
                void navigate("/staff/new");
              }}
              className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg shadow-xs h-8"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>{t("staff.newStaff", "Add Employee")}</span>
            </Button>
          </Can>
        </div>
      </div>

      {/* TOP KPI CARDS (Compact & Role-Guarded) */}
      <div
        className={`grid gap-3 ${
          isSuperAdmin
            ? "grid-cols-2 sm:grid-cols-2 lg:grid-cols-4"
            : "grid-cols-1 sm:grid-cols-3"
        }`}
      >
        {/* Super Admin Card - ONLY visible to Super Admin */}
        {isSuperAdmin && (
          <button
            type="button"
            onClick={() => setActiveSection(activeSection === "SUPERADMIN" ? "ALL" : "SUPERADMIN")}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer select-none bg-white dark:bg-slate-900 hover:shadow-xs ${
              activeSection === "SUPERADMIN"
                ? "border-indigo-500 ring-2 ring-indigo-500/20 shadow-xs"
                : "border-indigo-200/80 dark:border-indigo-900/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                {t("staff.kpiSuperAdmin", "Super Admin")}
              </span>
              <div className="h-7 w-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/70 dark:border-indigo-800 flex items-center justify-center text-indigo-700 dark:text-indigo-400">
                <ShieldCheck className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-mono">
                {isSummaryLoading ? "—" : summaryData?.superadmin ?? superadminList.length}
              </span>
              <span className="text-[10px] text-indigo-600 dark:text-indigo-400 font-medium">
                {t("common.active", "Active")}
              </span>
            </div>
          </button>
        )}

        {/* Administration Card */}
        <button
          type="button"
          onClick={() => setActiveSection(activeSection === "ADMIN" ? "ALL" : "ADMIN")}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer select-none bg-white dark:bg-slate-900 hover:shadow-xs ${
            activeSection === "ADMIN"
              ? "border-sky-500 ring-2 ring-sky-500/20 shadow-xs"
              : "border-sky-200/80 dark:border-sky-900/50"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              {t("staff.kpiAdmin", "Administration")}
            </span>
            <div className="h-7 w-7 rounded-lg bg-sky-50 dark:bg-sky-950/60 border border-sky-200/70 dark:border-sky-800 flex items-center justify-center text-sky-700 dark:text-sky-400">
              <UserCog className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-mono">
              {isSummaryLoading ? "—" : summaryData?.admin ?? adminList.length}
            </span>
            <span className="text-[10px] text-sky-600 dark:text-sky-400 font-medium">
              Officers
            </span>
          </div>
        </button>

        {/* Teachers Card */}
        <button
          type="button"
          onClick={() => setActiveSection(activeSection === "TEACHER" ? "ALL" : "TEACHER")}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer select-none bg-white dark:bg-slate-900 hover:shadow-xs ${
            activeSection === "TEACHER"
              ? "border-emerald-500 ring-2 ring-emerald-500/20 shadow-xs"
              : "border-emerald-200/80 dark:border-emerald-900/50"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              {t("staff.kpiTeacher", "Teachers & Faculty")}
            </span>
            <div className="h-7 w-7 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/70 dark:border-emerald-800 flex items-center justify-center text-emerald-700 dark:text-emerald-400">
              <GraduationCap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-mono">
              {isSummaryLoading ? "—" : summaryData?.teacher ?? teacherList.length}
            </span>
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
              Faculty
            </span>
          </div>
        </button>

        {/* Support Staff Card */}
        <button
          type="button"
          onClick={() => setActiveSection(activeSection === "STAFF" ? "ALL" : "STAFF")}
          className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer select-none bg-white dark:bg-slate-900 hover:shadow-xs ${
            activeSection === "STAFF"
              ? "border-amber-500 ring-2 ring-amber-500/20 shadow-xs"
              : "border-amber-200/80 dark:border-amber-900/50"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              {t("staff.kpiStaff", "Support Staff")}
            </span>
            <div className="h-7 w-7 rounded-lg bg-amber-50 dark:bg-amber-950/60 border border-amber-200/70 dark:border-amber-800 flex items-center justify-center text-amber-700 dark:text-amber-400">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 font-mono">
              {isSummaryLoading ? "—" : summaryData?.staff ?? supportStaffList.length}
            </span>
            <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">
              General
            </span>
          </div>
        </button>
      </div>

      {/* Filter Toolbar & Quick Section Selector */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3 sm:p-3.5 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2.5">
          {/* Search Bar with instant Clear Button */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder={t(
                "staff.searchPlaceholder",
                "Search by name, employee ID, phone, or NID..."
              )}
              className="h-8 pl-8 pr-8 text-xs rounded-lg border-slate-200 dark:border-slate-800"
            />
            {search && (
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  setDebouncedSearch("");
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                aria-label="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 sm:flex sm:items-center gap-2">
            {/* Department Filter */}
            <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
              <SelectTrigger className="h-8 min-w-[130px] text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("staff.filterDepartment", "Department: All")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">
                  {t("staff.allDepartments", "All Departments")}
                </SelectItem>
                {departments.map((d) => (
                  <SelectItem key={d.id} value={d.id} className="text-xs">
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-8 min-w-[110px] text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("staff.filterStatus", "Status: All")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">
                  {t("staff.allStatuses", "All Status")}
                </SelectItem>
                <SelectItem value="active" className="text-xs">
                  {t("common.active", "Active")}
                </SelectItem>
                <SelectItem value="on_leave" className="text-xs">
                  {t("staff.onLeave", "On Leave")}
                </SelectItem>
                <SelectItem value="resigned" className="text-xs">
                  {t("staff.resigned", "Resigned")}
                </SelectItem>
                <SelectItem value="retired" className="text-xs">
                  {t("staff.retired", "Retired")}
                </SelectItem>
              </SelectContent>
            </Select>

            {/* Reset Filters Button */}
            {(debouncedSearch ||
              departmentFilter !== "ALL" ||
              statusFilter !== "ALL" ||
              activeSection !== "ALL") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetFilters}
                className="col-span-2 sm:col-span-1 h-8 px-2.5 text-xs text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 border sm:border-0 border-slate-200 dark:border-slate-800 rounded-lg"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                <span>{t("common.reset", "Reset")}</span>
              </Button>
            )}
          </div>
        </div>

        {/* Quick Section Jump Pills (Scrollable on small screens) */}
        <div className="flex items-center gap-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/60 overflow-x-auto no-scrollbar">
          <button
            type="button"
            onClick={() => setActiveSection("ALL")}
            className={`shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
              activeSection === "ALL"
                ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 shadow-2xs"
                : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
            }`}
          >
            {t("staff.allCategories", "All Roles")} ({rawStaffList.length})
          </button>

          {isSuperAdmin && (
            <button
              type="button"
              onClick={() => setActiveSection("SUPERADMIN")}
              className={`shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                activeSection === "SUPERADMIN"
                  ? "bg-indigo-700 text-white shadow-2xs"
                  : "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100"
              }`}
            >
              <ShieldCheck className="h-3 w-3" />
              <span>{t("staff.kpiSuperAdmin", "Super Admin")}</span>
              <span className="font-mono text-[10px]">({superadminList.length})</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setActiveSection("ADMIN")}
            className={`shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
              activeSection === "ADMIN"
                ? "bg-sky-700 text-white shadow-2xs"
                : "bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 hover:bg-sky-100"
            }`}
          >
            <UserCog className="h-3 w-3" />
            <span>{t("staff.kpiAdmin", "Administration")}</span>
            <span className="font-mono text-[10px]">({adminList.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSection("TEACHER")}
            className={`shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
              activeSection === "TEACHER"
                ? "bg-emerald-800 text-white shadow-2xs"
                : "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 hover:bg-emerald-100"
            }`}
          >
            <GraduationCap className="h-3 w-3" />
            <span>{t("staff.kpiTeacher", "Teachers")}</span>
            <span className="font-mono text-[10px]">({teacherList.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSection("STAFF")}
            className={`shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
              activeSection === "STAFF"
                ? "bg-amber-700 text-white shadow-2xs"
                : "bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 hover:bg-amber-100"
            }`}
          >
            <Users className="h-3 w-3" />
            <span>{t("staff.kpiStaff", "Support Staff")}</span>
            <span className="font-mono text-[10px]">({supportStaffList.length})</span>
          </button>
        </div>
      </div>

      {/* SECTION-WISE SEPARATED DIRECTORY */}
      {isLoading ? (
        <div className="py-20 text-center rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="inline-flex items-center gap-2 text-slate-500 text-xs">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
            <span>{t("common.loading", "Loading staff roster...")}</span>
          </div>
        </div>
      ) : isError ? (
        <div className="py-16 text-center rounded-xl border border-rose-200 bg-rose-50/50 dark:bg-rose-950/20 text-rose-700 text-xs">
          <span>{t("common.errorLoading", "Failed to load staff roster.")}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void refetch();
            }}
            className="ml-3 text-xs h-7"
          >
            {t("common.retry", "Retry")}
          </Button>
        </div>
      ) : rawStaffList.length === 0 ? (
        <div className="py-16 text-center rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-400 mb-2.5">
            <Users className="h-5 w-5" />
          </div>
          <p className="text-xs sm:text-sm font-semibold text-slate-700 dark:text-slate-300">
            {t("staff.noStaffFound", "No employees found")}
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            {debouncedSearch || departmentFilter !== "ALL" || statusFilter !== "ALL"
              ? t("students.adjustFilters", "Try adjusting your search criteria or filters.")
              : t("staff.getStarted", "Begin by onboarding new teachers and staff.")}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Section 1: Super Admin (Visible ONLY to Super Admin) */}
          {isSuperAdmin && (activeSection === "ALL" || activeSection === "SUPERADMIN") &&
            renderStaffSection(
              "SUPERADMIN",
              t("staff.sectionSuperAdmin", "Super Administrators"),
              <ShieldCheck className="h-4 w-4 text-indigo-700 dark:text-indigo-400" />,
              superadminList,
              {
                border: "border-indigo-200/90 dark:border-indigo-900/60",
                headerBg: "bg-indigo-50/70 dark:bg-indigo-950/30",
                badgeBg: "bg-indigo-100 dark:bg-indigo-900/60",
                badgeText: "text-indigo-800 dark:text-indigo-300",
              }
            )}

          {/* Section 2: Administration */}
          {(activeSection === "ALL" || activeSection === "ADMIN") &&
            renderStaffSection(
              "ADMIN",
              t("staff.sectionAdmin", "Administrative Officers & Leadership"),
              <UserCog className="h-4 w-4 text-sky-700 dark:text-sky-400" />,
              adminList,
              {
                border: "border-sky-200/90 dark:border-sky-900/60",
                headerBg: "bg-sky-50/70 dark:bg-sky-950/30",
                badgeBg: "bg-sky-100 dark:bg-sky-900/60",
                badgeText: "text-sky-800 dark:text-sky-300",
              }
            )}

          {/* Section 3: Teachers & Faculty */}
          {(activeSection === "ALL" || activeSection === "TEACHER") &&
            renderStaffSection(
              "TEACHER",
              t("staff.sectionTeacher", "Teaching Faculty & Educators"),
              <GraduationCap className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />,
              teacherList,
              {
                border: "border-emerald-200/90 dark:border-emerald-900/60",
                headerBg: "bg-emerald-50/70 dark:bg-emerald-950/30",
                badgeBg: "bg-emerald-100 dark:bg-emerald-900/60",
                badgeText: "text-emerald-800 dark:text-emerald-300",
              }
            )}

          {/* Section 4: General & Support Staff */}
          {(activeSection === "ALL" || activeSection === "STAFF") &&
            renderStaffSection(
              "STAFF",
              t("staff.sectionStaff", "Support, Logistics & Facilities Personnel"),
              <Users className="h-4 w-4 text-amber-700 dark:text-amber-400" />,
              supportStaffList,
              {
                border: "border-amber-200/90 dark:border-amber-900/60",
                headerBg: "bg-amber-50/70 dark:bg-amber-950/30",
                badgeBg: "bg-amber-100 dark:bg-amber-900/60",
                badgeText: "text-amber-800 dark:text-amber-300",
              }
            )}
        </div>
      )}
    </div>
  );
}

export default StaffListPage;
