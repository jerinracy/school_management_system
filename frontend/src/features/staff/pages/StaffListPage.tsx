import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  Download,
  GraduationCap,
  Plus,
  RotateCcw,
  Search,
  UserCheck,
  Users,
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

export function StaffListPage() {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language === "bn" ? "bn" : "en";
  const navigate = useNavigate();

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  const [staffTypeFilter, setStaffTypeFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [page, setPage] = useState(1);

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
        staff_type: staffTypeFilter !== "ALL" ? staffTypeFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        page,
      },
    ],
    queryFn: () =>
      staffApi.getStaffList({
        search: debouncedSearch || undefined,
        department: departmentFilter !== "ALL" ? departmentFilter : undefined,
        staff_type: staffTypeFilter !== "ALL" ? staffTypeFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        page,
      }),
  });

  const staffList: StaffListItem[] = data?.results ?? [];
  const totalCount = data?.count ?? 0;

  // Search Debouncing
  const handleSearchChange = (value: string) => {
    setSearch(value);
    const timeout = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 300);
    return () => clearTimeout(timeout);
  };

  const handleResetFilters = () => {
    setSearch("");
    setDebouncedSearch("");
    setDepartmentFilter("ALL");
    setStaffTypeFilter("ALL");
    setStatusFilter("ALL");
    setPage(1);
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
            {t("common.active", "Active")}
          </span>
        );
      case "on_leave":
        return (
          <span className="inline-flex items-center rounded-md bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60">
            {t("staff.onLeave", "On Leave")}
          </span>
        );
      case "resigned":
      case "terminated":
      case "retired":
        return (
          <span className="inline-flex items-center rounded-md bg-rose-50 dark:bg-rose-950/60 px-2 py-0.5 text-xs font-semibold text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60">
            {status.toUpperCase()}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            {status || t("common.active", "Active")}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("staff.directoryTitle", "Staff & Faculty Directory")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {t(
              "staff.directorySubtitle",
              "Manage institutional employees, teachers, designations, and leave records.",
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/staff/departments">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs rounded-lg">
              <Briefcase className="h-3.5 w-3.5" />
              <span>{t("staff.departmentsLink", "Departments & Designations")}</span>
            </Button>
          </Link>

          <Link to="/staff/leaves">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs rounded-lg">
              <UserCheck className="h-3.5 w-3.5" />
              <span>{t("staff.leavesLink", "Leave Management")}</span>
            </Button>
          </Link>

          <a
            href={staffApi.getExportUrl()}
            download
            className="inline-flex items-center justify-center gap-1.5 h-9 px-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-2xs"
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t("common.export", "Export Excel")}</span>
          </a>

          <Can perm="staff.manage">
            <Button
              size="sm"
              onClick={() => {
                void navigate("/staff/new");
              }}
              className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>{t("staff.newStaff", "Add Employee")}</span>
            </Button>
          </Can>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5 shadow-2xs">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          {/* Search Bar */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder={t(
                "staff.searchPlaceholder",
                "Search by name, employee ID, phone, or NID...",
              )}
              className="h-9 pl-9 text-xs rounded-lg border-slate-200 dark:border-slate-800"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Department Filter */}
            <Select value={departmentFilter} onValueChange={(val) => { setDepartmentFilter(val); setPage(1); }}>
              <SelectTrigger className="h-9 min-w-[140px] text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("staff.filterDepartment", "Department: All")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">{t("staff.allDepartments", "All Departments")}</SelectItem>
                {departments.map((d) => (
                  <SelectItem key={d.id} value={d.id} className="text-xs">
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Staff Type Filter */}
            <Select value={staffTypeFilter} onValueChange={(val) => { setStaffTypeFilter(val); setPage(1); }}>
              <SelectTrigger className="h-9 min-w-[130px] text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("staff.filterType", "Type: All")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">{t("staff.allTypes", "All Roles")}</SelectItem>
                <SelectItem value="teacher" className="text-xs">Teacher</SelectItem>
                <SelectItem value="admin" className="text-xs">Admin</SelectItem>
                <SelectItem value="support" className="text-xs">Support</SelectItem>
                <SelectItem value="driver" className="text-xs">Driver</SelectItem>
                <SelectItem value="security" className="text-xs">Security</SelectItem>
                <SelectItem value="other" className="text-xs">Other</SelectItem>
              </SelectContent>
            </Select>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={(val) => { setStatusFilter(val); setPage(1); }}>
              <SelectTrigger className="h-9 min-w-[120px] text-xs rounded-lg border-slate-200 dark:border-slate-800">
                <SelectValue placeholder={t("staff.filterStatus", "Status: All")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL" className="text-xs">{t("staff.allStatuses", "All Status")}</SelectItem>
                <SelectItem value="active" className="text-xs">{t("common.active", "Active")}</SelectItem>
                <SelectItem value="on_leave" className="text-xs">{t("staff.onLeave", "On Leave")}</SelectItem>
                <SelectItem value="resigned" className="text-xs">{t("staff.resigned", "Resigned")}</SelectItem>
                <SelectItem value="retired" className="text-xs">{t("staff.retired", "Retired")}</SelectItem>
              </SelectContent>
            </Select>

            {/* Reset Filters */}
            {(debouncedSearch || departmentFilter !== "ALL" || staffTypeFilter !== "ALL" || statusFilter !== "ALL") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetFilters}
                className="h-9 px-2 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1" />
                <span>{t("common.reset", "Reset")}</span>
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Staff Roster Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">{t("staff.employee", "Employee")}</th>
                <th className="px-4 py-3">{t("staff.designationDept", "Designation & Dept")}</th>
                <th className="px-4 py-3">{t("staff.contact", "Contact")}</th>
                <th className="px-4 py-3">{t("staff.roleType", "Role & MPO")}</th>
                <th className="px-4 py-3">{t("common.status", "Status")}</th>
                <th className="px-4 py-3 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <div className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                      <span>{t("common.loading", "Loading staff roster...")}</span>
                    </div>
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-danger">
                    <span>{t("common.errorLoading", "Failed to load staff roster.")}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => { void refetch(); }}
                      className="ml-2 text-xs"
                    >
                      {t("common.retry", "Retry")}
                    </Button>
                  </td>
                </tr>
              ) : staffList.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-400 mb-3">
                      <Users className="h-6 w-6" />
                    </div>
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                      {t("staff.noStaffFound", "No employees found")}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {debouncedSearch || departmentFilter !== "ALL" || staffTypeFilter !== "ALL"
                        ? t("students.adjustFilters", "Try adjusting your search criteria or filters.")
                        : t("staff.getStarted", "Begin by onboarding new teachers and staff.")}
                    </p>
                  </td>
                </tr>
              ) : (
                staffList.map((member) => (
                  <tr
                    key={member.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Employee Identity */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 shrink-0 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/80 dark:border-emerald-800 flex items-center justify-center font-bold text-xs text-emerald-800 dark:text-emerald-300 overflow-hidden">
                          {member.photo ? (
                            <img src={member.photo} alt={member.full_name_en} className="h-full w-full object-cover" />
                          ) : (
                            member.full_name_en.slice(0, 2).toUpperCase()
                          )}
                        </div>
                        <div>
                          <Link
                            to={`/staff/${member.id}`}
                            className="font-bold text-slate-900 dark:text-slate-100 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors"
                          >
                            {currentLang === "bn" && member.full_name_bn ? member.full_name_bn : member.full_name_en}
                          </Link>
                          <p className="text-[11px] font-mono text-slate-400">
                            {member.employee_id}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* Designation & Department */}
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {member.designation_title || "—"}
                        </span>
                        <p className="text-[11px] text-slate-500">
                          {member.department_name || "—"}
                        </p>
                      </div>
                    </td>

                    {/* Contact */}
                    <td className="px-4 py-3">
                      <div className="space-y-0.5 text-[11px]">
                        <span className="font-mono font-medium text-slate-700 dark:text-slate-300 block">
                          {member.phone}
                        </span>
                        {member.email && (
                          <span className="text-slate-400 font-mono truncate block max-w-[160px]">
                            {member.email}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Role Type & MPO */}
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="inline-flex items-center gap-1 rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-medium capitalize text-slate-700 dark:text-slate-300">
                          {member.staff_type === "teacher" && <GraduationCap className="h-3 w-3 text-emerald-600" />}
                          {(member.staff_type ?? "").replace("_", " ")}
                        </span>
                        {member.is_mpo && (
                          <span className="inline-flex items-center rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/50 px-1.5 py-0.2 text-[10px] font-bold">
                            MPO
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      {getStatusBadge(member.status)}
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          void navigate(`/staff/${member.id}`);
                        }}
                        className="h-8 px-2.5 text-xs text-emerald-800 dark:text-emerald-400 hover:text-emerald-900 hover:bg-emerald-50 rounded-lg"
                      >
                        <span>{t("common.view", "View")}</span>
                        <span className="ml-1">&rarr;</span>
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {totalCount > 20 && (
          <div className="flex items-center justify-between border-t border-slate-200 dark:border-slate-800 px-4 py-3 text-xs text-slate-500">
            <div>
              {t("common.showing", "Showing")} <span className="font-semibold text-slate-800 dark:text-slate-200">{staffList.length}</span> {t("common.of", "of")}{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">{totalCount}</span> {t("staff.employees", "employees")}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-8 text-xs rounded-lg"
              >
                {t("common.previous", "Previous")}
              </Button>
              <span className="text-xs font-mono px-1">{page}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={page * 20 >= totalCount}
                onClick={() => setPage((p) => p + 1)}
                className="h-8 text-xs rounded-lg"
              >
                {t("common.next", "Next")}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default StaffListPage;
