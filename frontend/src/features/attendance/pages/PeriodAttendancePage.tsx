import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Layers,
  Save,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { attendanceApi } from "@/features/attendance/api/attendanceApi";
import { academicApi } from "@/features/academics/api/academicApi";
import { studentsApi } from "@/features/students/api/studentsApi";

export default function PeriodAttendancePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const todayStr = useMemo(() => new Date().toISOString().split("T")[0] ?? "2026-01-01", []);
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedSection, setSelectedSection] = useState<string>("");
  const [selectedSubject, setSelectedSubject] = useState<string>("");

  const [studentStatuses, setStudentStatuses] = useState<Record<string, "present" | "absent" | "late" | "excused">>({});
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Queries
  const { data: classesData } = useQuery({
    queryKey: ["period-classes"],
    queryFn: () => academicApi.getClasses(),
  });

  const { data: sectionsData } = useQuery({
    queryKey: ["period-sections", selectedClass],
    queryFn: () => academicApi.getSections(selectedClass || undefined),
    enabled: Boolean(selectedClass),
  });

  const { data: subjectsData } = useQuery({
    queryKey: ["period-subjects", selectedClass],
    queryFn: () => academicApi.getSubjects(),
    enabled: Boolean(selectedClass),
  });

  const { data: studentsData, isLoading: isStudentsLoading } = useQuery({
    queryKey: ["period-students", selectedSection],
    queryFn: () => studentsApi.getStudents({ status: "active" }),
    enabled: Boolean(selectedSection),
  });

  const classes = classesData ?? [];
  const sections = sectionsData ?? [];
  const subjects = subjectsData ?? [];
  const students = studentsData?.results ?? [];

  // Bulk Submit Mutation
  const submitMutation = useMutation({
    mutationFn: () => {
      const records = students.map((s) => ({
        student_id: s.id,
        status: studentStatuses[s.id] || "present",
      }));

      return attendanceApi.bulkSubmitPeriodAttendance({
        date: selectedDate,
        section: selectedSection,
        subject: selectedSubject,
        records,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["attendance-periods"] });
      setNotification({ message: t("attendance.periodSubmitted", "Period roll call registered successfully."), type: "success" });
    },
    onError: (err: unknown) => {
      setNotification({ message: (err as Error).message || "Submission failed.", type: "error" });
    },
  });

  const handleMarkAll = (status: "present" | "absent" | "late" | "excused") => {
    const updated: Record<string, "present" | "absent" | "late" | "excused"> = {};
    students.forEach((s) => {
      updated[s.id] = status;
    });
    setStudentStatuses(updated);
  };

  const getStatusForStudent = (id: string): "present" | "absent" | "late" | "excused" => {
    return studentStatuses[id] || "present";
  };

  const setStatusForStudent = (id: string, status: "present" | "absent" | "late" | "excused") => {
    setStudentStatuses((prev) => ({ ...prev, [id]: status }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Link to="/attendance">
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-lg">
              <ArrowLeft className="h-4 w-4 text-slate-600 dark:text-slate-400" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {t("attendance.periodRegisterTitle", "Period-by-Period Classroom Attendance Register")}
            </h1>
            <p className="text-xs text-slate-500">
              {t(
                "attendance.periodRegisterSubtitle",
                "Subject course period roll call marking and lesson attendance tracking."
              )}
            </p>
          </div>
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

      {/* Selector Ribbon */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label htmlFor="period-date" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Session Date</label>
            <input
              id="period-date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs font-mono dark:border-slate-700 dark:bg-slate-900"
            />
          </div>

          <div>
            <label htmlFor="period-class" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Class Grade</label>
            <select
              id="period-class"
              value={selectedClass}
              onChange={(e) => {
                setSelectedClass(e.target.value);
                setSelectedSection("");
                setSelectedSubject("");
              }}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">Select Class...</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="period-section" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Section</label>
            <select
              id="period-section"
              value={selectedSection}
              disabled={!selectedClass}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50"
            >
              <option value="">Select Section...</option>
              {sections.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="period-subject" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Subject / Course</label>
            <select
              id="period-subject"
              value={selectedSubject}
              disabled={!selectedClass}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50"
            >
              <option value="">Select Subject...</option>
              {subjects.map((sub) => (
                <option key={sub.id} value={sub.id}>
                  {sub.name_en || sub.name_bn} ({sub.code})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Roll Call Register */}
      {!selectedSection || !selectedSubject ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-12 text-center text-xs text-slate-500">
          <Layers className="h-8 w-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">Select Class, Section, and Subject</p>
          <p className="text-slate-400 mt-0.5">The student roster for this period will load automatically.</p>
        </div>
      ) : isStudentsLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
        </div>
      ) : students.length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-500 rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          No active students enrolled in this section.
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden space-y-4 p-4">
          {/* Quick Mark Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-slate-500 font-medium mr-2">Quick Assign All:</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleMarkAll("present")}
                className="h-7 px-2 text-[11px] text-emerald-700 hover:bg-emerald-50"
              >
                All Present
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleMarkAll("absent")}
                className="h-7 px-2 text-[11px] text-rose-700 hover:bg-rose-50"
              >
                All Absent
              </Button>
            </div>

            <Button
              size="sm"
              disabled={submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
              className="gap-1.5 text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg h-8"
            >
              <Save className="h-3.5 w-3.5" />
              <span>{submitMutation.isPending ? "Submitting..." : "Save Period Register"}</span>
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Student Name</th>
                  <th className="px-4 py-2.5 font-semibold font-mono">Roll / Student ID</th>
                  <th className="px-4 py-2.5 font-semibold text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {students.map((s) => {
                  const status = getStatusForStudent(s.id);
                  return (
                    <tr key={s.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-2.5 font-semibold text-slate-900 dark:text-slate-100">
                        {s.name_en}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-slate-600 dark:text-slate-400">
                        {s.student_id}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <div className="inline-flex items-center gap-1 rounded-lg border border-slate-200 p-0.5 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
                          <button
                            type="button"
                            onClick={() => setStatusForStudent(s.id, "present")}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              status === "present"
                                ? "bg-emerald-700 text-white shadow-2xs"
                                : "text-slate-500 hover:text-slate-800"
                            }`}
                          >
                            Present
                          </button>
                          <button
                            type="button"
                            onClick={() => setStatusForStudent(s.id, "late")}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              status === "late"
                                ? "bg-amber-600 text-white shadow-2xs"
                                : "text-slate-500 hover:text-slate-800"
                            }`}
                          >
                            Late
                          </button>
                          <button
                            type="button"
                            onClick={() => setStatusForStudent(s.id, "absent")}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              status === "absent"
                                ? "bg-rose-700 text-white shadow-2xs"
                                : "text-slate-500 hover:text-slate-800"
                            }`}
                          >
                            Absent
                          </button>
                          <button
                            type="button"
                            onClick={() => setStatusForStudent(s.id, "excused")}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              status === "excused"
                                ? "bg-blue-700 text-white shadow-2xs"
                                : "text-slate-500 hover:text-slate-800"
                            }`}
                          >
                            Excused
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
