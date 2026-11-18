import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  Clock,
  GraduationCap,
  Layers,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  UserCheck,
  Users,
  X,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  attendanceApi,
  type DailyAttendanceItem,
} from "@/features/attendance/api/attendanceApi";
import { studentsApi } from "@/features/students/api/studentsApi";
import { staffApi } from "@/features/staff/api/staffApi";
import { academicApi } from "@/features/academics/api/academicApi";

export default function DailyAttendancePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const todayStr = useMemo(() => new Date().toISOString().split("T")[0] ?? "2026-01-01", []);
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);
  const [userType, setUserType] = useState<"student" | "staff">("student");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [selectedClass, setSelectedClass] = useState("ALL");
  const [selectedDepartment, setSelectedDepartment] = useState("ALL");

  // Recompute & Manual Modals
  const [showRecomputeModal, setShowRecomputeModal] = useState(false);
  const [recomputeStartDate, setRecomputeStartDate] = useState(todayStr);
  const [recomputeEndDate, setRecomputeEndDate] = useState(todayStr);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [batchActionStatus, setBatchActionStatus] = useState<"present" | "absent" | "late">("present");

  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Queries
  const { data: attendanceData, isLoading } = useQuery({
    queryKey: ["daily-attendance", selectedDate, userType, statusFilter],
    queryFn: () =>
      attendanceApi.getDailyAttendance({
        date: selectedDate,
        user_type: userType,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      }),
  });

  const { data: classesData } = useQuery({
    queryKey: ["attendance-classes-list"],
    queryFn: () => academicApi.getClasses(),
    enabled: userType === "student",
  });

  const { data: departmentsData } = useQuery({
    queryKey: ["attendance-departments-list"],
    queryFn: () => staffApi.getDepartments(),
    enabled: userType === "staff",
  });

  const { data: studentsData } = useQuery({
    queryKey: ["attendance-students-lookup"],
    queryFn: () => studentsApi.getStudents({ status: "active" }),
    enabled: showBatchModal && userType === "student",
  });

  const { data: staffMembersData } = useQuery({
    queryKey: ["attendance-staff-lookup"],
    queryFn: () => staffApi.getStaffList({ status: "active" }),
    enabled: showBatchModal && userType === "staff",
  });

  // Recompute Mutation
  const recomputeMutation = useMutation({
    mutationFn: () =>
      attendanceApi.recomputeAttendance({
        start_date: recomputeStartDate,
        end_date: recomputeEndDate,
        user_type: userType,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["daily-attendance"] });
      setShowRecomputeModal(false);
      setNotification({ message: t("attendance.recomputeSuccess", "Attendance recomputed successfully against active shifts and policies."), type: "success" });
    },
    onError: (err: unknown) => {
      setNotification({ message: (err as Error).message || "Recompute failed.", type: "error" });
    },
  });

  // Quick In-Place Status Update Mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ record, newStatus }: { record: DailyAttendanceItem; newStatus: "present" | "late" | "absent" | "half_day" | "leave" | "holiday" }) =>
      attendanceApi.bulkManualAttendance({
        date: selectedDate,
        user_type: userType,
        records: [
          {
            student_id: record.student || undefined,
            staff_id: record.staff || undefined,
            status: newStatus,
            remarks: "Manual override from daily attendance sheet",
          },
        ],
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["daily-attendance"] });
    },
    onError: (err: unknown) => {
      setNotification({ message: (err as Error).message || "Update failed.", type: "error" });
    },
  });

  // Batch Manual Roll Call Mutation
  const batchManualMutation = useMutation({
    mutationFn: () => {
      if (userType === "student") {
        const studentList = studentsData?.results ?? [];
        return attendanceApi.bulkManualAttendance({
          date: selectedDate,
          user_type: "student",
          records: studentList.map((s) => ({
            student_id: s.id,
            status: batchActionStatus,
            remarks: `Batch roll call marked as ${batchActionStatus}`,
          })),
        });
      } else {
        const staffList = staffMembersData?.results ?? [];
        return attendanceApi.bulkManualAttendance({
          date: selectedDate,
          user_type: "staff",
          records: staffList.map((s) => ({
            staff_id: s.id,
            status: batchActionStatus,
            remarks: `Batch roll call marked as ${batchActionStatus}`,
          })),
        });
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["daily-attendance"] });
      setShowBatchModal(false);
      setNotification({ message: t("attendance.batchSuccess", "Batch attendance submitted successfully."), type: "success" });
    },
    onError: (err: unknown) => {
      setNotification({ message: (err as Error).message || "Batch submission failed.", type: "error" });
    },
  });

  const records = useMemo(() => attendanceData?.results ?? [], [attendanceData]);
  const classes = useMemo(() => classesData ?? [], [classesData]);
  const departments = useMemo(() => departmentsData?.results ?? [], [departmentsData]);

  // Filtered Records by search query
  const filteredRecords = useMemo(() => {
    return records.filter((r) => {
      const name = (r.student_name || r.staff_name || "").toLowerCase();
      const id = (r.student_roll || r.staff_employee_id || "").toLowerCase();
      const q = search.trim().toLowerCase();
      return !q || name.includes(q) || id.includes(q);
    });
  }, [records, search]);

  // Statistics
  const totalCount = records.length;
  const presentCount = records.filter((r) => r.status === "present").length;
  const lateCount = records.filter((r) => r.status === "late").length;
  const absentCount = records.filter((r) => r.status === "absent").length;
  const leaveCount = records.filter((r) => r.status === "leave" || r.status === "half_day").length;
  const attendanceRate = totalCount > 0 ? Math.round(((presentCount + lateCount) / totalCount) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("attendance.title", "Daily Attendance Management")}
          </h1>
          <p className="text-xs text-slate-500">
            {t(
              "attendance.subtitle",
              "Biometric punch sync, daily roll call, shift grace limits, and attendance audits."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/attendance/corrections">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs rounded-lg">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>{t("attendance.correctionsLink", "Corrections Queue")}</span>
            </Button>
          </Link>

          <Link to="/attendance/periods">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs rounded-lg">
              <Layers className="h-3.5 w-3.5" />
              <span>{t("attendance.periodsLink", "Period Register")}</span>
            </Button>
          </Link>

          <Link to="/attendance/policies">
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs rounded-lg">
              <Settings className="h-3.5 w-3.5" />
              <span>{t("attendance.policiesLink", "Policies & Shifts")}</span>
            </Button>
          </Link>

          <Button
            size="sm"
            onClick={() => setShowBatchModal(true)}
            className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg h-9 shadow-xs"
          >
            <UserCheck className="h-4 w-4" />
            <span>{t("attendance.batchRollCall", "Batch Roll Call")}</span>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
          <span className="text-[11px] font-medium text-slate-400 block">{t("attendance.total", "Total Roster")}</span>
          <span className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">{totalCount}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
          <span className="text-[11px] font-medium text-emerald-600 block">{t("attendance.present", "Present")}</span>
          <span className="text-xl font-bold font-mono text-emerald-700 dark:text-emerald-400">{presentCount}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
          <span className="text-[11px] font-medium text-amber-600 block">{t("attendance.late", "Late Arrival")}</span>
          <span className="text-xl font-bold font-mono text-amber-700 dark:text-amber-400">{lateCount}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
          <span className="text-[11px] font-medium text-rose-600 block">{t("attendance.absent", "Absent")}</span>
          <span className="text-xl font-bold font-mono text-rose-700 dark:text-rose-400">{absentCount}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
          <span className="text-[11px] font-medium text-blue-600 block">{t("attendance.onLeave", "Leave / Half Day")}</span>
          <span className="text-xl font-bold font-mono text-blue-700 dark:text-blue-400">{leaveCount}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
          <span className="text-[11px] font-medium text-slate-400 block">{t("attendance.rate", "Turnout Rate")}</span>
          <span className="text-xl font-bold font-mono text-emerald-800 dark:text-emerald-300">{attendanceRate}%</span>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          className={`flex items-center justify-between rounded-lg p-3 text-xs ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? <CheckCircle2 className="h-4 w-4 shrink-0" /> : <AlertCircle className="h-4 w-4 shrink-0" />}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="hover:opacity-75">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Control Bar: Date Selector, User Type Switcher, Filters */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* User Type Switcher */}
          <div className="inline-flex rounded-lg border border-slate-200 dark:border-slate-800 p-1 bg-slate-50 dark:bg-slate-800/60 text-xs">
            <button
              onClick={() => setUserType("student")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                userType === "student"
                  ? "bg-white dark:bg-slate-900 text-emerald-800 dark:text-emerald-400 shadow-xs"
                  : "text-slate-500 hover:text-slate-900 dark:text-slate-400"
              }`}
            >
              <GraduationCap className="h-3.5 w-3.5" />
              <span>{t("attendance.students", "Students")}</span>
            </button>
            <button
              onClick={() => setUserType("staff")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                userType === "staff"
                  ? "bg-white dark:bg-slate-900 text-emerald-800 dark:text-emerald-400 shadow-xs"
                  : "text-slate-500 hover:text-slate-900 dark:text-slate-400"
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              <span>{t("attendance.staffFaculty", "Staff & Faculty")}</span>
            </button>
          </div>

          {/* Date Picker & Recompute Engine Button */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs dark:border-slate-800 dark:bg-slate-900">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-transparent font-mono focus:outline-hidden"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRecomputeModal(true)}
              className="h-8 gap-1.5 text-xs text-slate-700 dark:text-slate-300"
            >
              <RefreshCw className="h-3 w-3" />
              <span>{t("attendance.recompute", "Recompute Engine")}</span>
            </Button>
          </div>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
          <div className="relative w-56">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={userType === "student" ? "Search by name, roll..." : "Search by name, employee ID..."}
              className="pl-8 text-xs h-8 rounded-lg"
            />
          </div>

          {userType === "student" && (
            <select
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs focus:outline-hidden dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="ALL">All Classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}

          {userType === "staff" && (
            <select
              value={selectedDepartment}
              onChange={(e) => setSelectedDepartment(e.target.value)}
              className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs focus:outline-hidden dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="ALL">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          )}

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 rounded-lg border border-slate-300 bg-white px-2.5 text-xs focus:outline-hidden dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="ALL">All Statuses</option>
            <option value="present">Present</option>
            <option value="late">Late Arrival</option>
            <option value="absent">Absent</option>
            <option value="half_day">Half Day</option>
            <option value="leave">On Leave</option>
          </select>
        </div>
      </div>

      {/* Attendance Register Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
          </div>
        ) : filteredRecords.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            {t("attendance.noRecords", "No attendance records found for the selected date and filters.")}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">{userType === "student" ? "Student" : "Staff Member"}</th>
                  <th className="px-4 py-3 font-semibold font-mono">{userType === "student" ? "Roll / ID" : "Employee ID"}</th>
                  <th className="px-4 py-3 font-semibold font-mono">{t("attendance.firstIn", "First In")}</th>
                  <th className="px-4 py-3 font-semibold font-mono">{t("attendance.lastOut", "Last Out")}</th>
                  <th className="px-4 py-3 font-semibold">{t("attendance.duration", "Work/Class Duration")}</th>
                  <th className="px-4 py-3 font-semibold">{t("attendance.status", "Attendance Status")}</th>
                  <th className="px-4 py-3 font-semibold text-right">{t("attendance.quickAction", "Quick Override")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredRecords.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                      {userType === "student" ? r.student_name || "Student" : r.staff_name || "Staff"}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                      {userType === "student" ? r.student_roll || "—" : r.staff_employee_id || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700 dark:text-slate-300">
                      {r.first_in ? r.first_in.slice(11, 16) : "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700 dark:text-slate-300">
                      {r.last_out ? r.last_out.slice(11, 16) : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                      {r.total_minutes ? `${Math.floor(r.total_minutes / 60)}h ${r.total_minutes % 60}m` : "—"}
                      {r.minutes_late ? (
                        <span className="text-amber-600 font-mono text-[11px] ml-1">
                          (+{r.minutes_late}m late)
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                          r.status === "present"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                            : r.status === "late"
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                            : r.status === "absent"
                            ? "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                            : "bg-blue-100 text-blue-800 dark:bg-blue-950/80 dark:text-blue-300"
                        }`}
                      >
                        {r.status === "present" && <CheckCircle2 className="h-3 w-3" />}
                        {r.status === "late" && <Clock className="h-3 w-3" />}
                        {r.status === "absent" && <XCircle className="h-3 w-3" />}
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <select
                        value={r.status}
                        onChange={(e) =>
                          updateStatusMutation.mutate({
                            record: r,
                            newStatus: e.target.value as "present" | "late" | "absent" | "half_day" | "leave" | "holiday",
                          })
                        }
                        className="h-7 rounded-md border border-slate-200 bg-white px-2 text-[11px] focus:outline-hidden dark:border-slate-700 dark:bg-slate-900"
                      >
                        <option value="present">Present</option>
                        <option value="late">Late</option>
                        <option value="absent">Absent</option>
                        <option value="half_day">Half Day</option>
                        <option value="leave">On Leave</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Recompute Attendance */}
      {showRecomputeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t("attendance.recomputeTitle", "Recompute Attendance Engine")}
              </h2>
              <button onClick={() => setShowRecomputeModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              {t(
                "attendance.recomputeDesc",
                "Reconcile raw biometric punches against institution shifts, grace minutes, half-day cutoffs, and leaves for the specified date window."
              )}
            </p>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label htmlFor="recompute-start" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Start Date</label>
                <Input
                  id="recompute-start"
                  type="date"
                  value={recomputeStartDate}
                  onChange={(e) => setRecomputeStartDate(e.target.value)}
                  className="h-9 text-xs font-mono"
                />
              </div>
              <div>
                <label htmlFor="recompute-end" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">End Date</label>
                <Input
                  id="recompute-end"
                  type="date"
                  value={recomputeEndDate}
                  onChange={(e) => setRecomputeEndDate(e.target.value)}
                  className="h-9 text-xs font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setShowRecomputeModal(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="sm"
                disabled={recomputeMutation.isPending}
                onClick={() => recomputeMutation.mutate()}
                className="bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {recomputeMutation.isPending ? t("common.processing", "Processing...") : t("attendance.runRecompute", "Execute Recompute")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Batch Roll Call */}
      {showBatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {t("attendance.batchRollCallTitle", "Batch Manual Roll Call")}
              </h2>
              <button onClick={() => setShowBatchModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400">
              Set attendance status for all {userType === "student" ? "enrolled students" : "active staff"} on{" "}
              <span className="font-mono font-bold text-slate-900 dark:text-slate-100">{selectedDate}</span>.
            </p>

            <div className="space-y-3 text-xs">
              <span className="block text-slate-600 dark:text-slate-400 font-medium">Bulk Assign Status</span>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setBatchActionStatus("present")}
                  className={`py-2 text-center rounded-lg border font-semibold ${
                    batchActionStatus === "present"
                      ? "border-emerald-700 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                      : "border-slate-200 text-slate-600 dark:border-slate-700"
                  }`}
                >
                  Mark All Present
                </button>
                <button
                  type="button"
                  onClick={() => setBatchActionStatus("absent")}
                  className={`py-2 text-center rounded-lg border font-semibold ${
                    batchActionStatus === "absent"
                      ? "border-rose-700 bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                      : "border-slate-200 text-slate-600 dark:border-slate-700"
                  }`}
                >
                  Mark All Absent
                </button>
                <button
                  type="button"
                  onClick={() => setBatchActionStatus("late")}
                  className={`py-2 text-center rounded-lg border font-semibold ${
                    batchActionStatus === "late"
                      ? "border-amber-700 bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                      : "border-slate-200 text-slate-600 dark:border-slate-700"
                  }`}
                >
                  Mark All Late
                </button>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setShowBatchModal(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="sm"
                disabled={batchManualMutation.isPending}
                onClick={() => batchManualMutation.mutate()}
                className="bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {batchManualMutation.isPending ? t("common.saving", "Saving...") : t("attendance.applyBatch", "Apply Roll Call")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
