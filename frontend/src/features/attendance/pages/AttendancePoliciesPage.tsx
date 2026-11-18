import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  Play,
  Plus,
  Sliders,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  attendanceApi,
  type AttendancePolicyItem,
} from "@/features/attendance/api/attendanceApi";
import {
  attendancePolicyFormSchema,
  type AttendancePolicyFormData,
} from "@/features/attendance/schemas/attendanceSchemas";

export default function AttendancePoliciesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [showAddModal, setShowAddModal] = useState(false);
  const [simulatingPolicy, setSimulatingPolicy] = useState<AttendancePolicyItem | null>(null);
  const [simulationPunchTime, setSimulationPunchTime] = useState("08:14");
  const [simulationResult, setSimulationResult] = useState<Record<string, unknown> | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Policies Query
  const { data: policiesData, isLoading } = useQuery({
    queryKey: ["attendance-policies"],
    queryFn: () => attendanceApi.getPolicies(),
  });

  // Form
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AttendancePolicyFormData>({
    resolver: zodResolver(attendancePolicyFormSchema) as never,
    defaultValues: {
      name: "Default Morning Shift Policy",
      user_type: "student",
      start_time: "08:00",
      end_time: "14:00",
      grace_minutes: 15,
      late_threshold_minutes: 30,
      half_day_threshold_minutes: 120,
      early_leave_threshold_minutes: 30,
      min_work_duration_minutes: 240,
      weekend_days: ["friday", "saturday"],
      is_active: true,
    },
  });

  // Create Policy Mutation
  const createPolicyMutation = useMutation({
    mutationFn: (data: AttendancePolicyFormData) =>
      attendanceApi.createPolicy({
        name: data.name,
        user_type: data.user_type,
        start_time: data.start_time,
        end_time: data.end_time,
        grace_minutes: Number(data.grace_minutes),
        late_threshold_minutes: Number(data.late_threshold_minutes),
        half_day_threshold_minutes: Number(data.half_day_threshold_minutes),
        early_leave_threshold_minutes: Number(data.early_leave_threshold_minutes),
        min_work_duration_minutes: Number(data.min_work_duration_minutes),
        weekend_days: data.weekend_days,
        is_active: data.is_active,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["attendance-policies"] });
      setShowAddModal(false);
      reset();
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError((err as Error).message || "Failed to save attendance policy.");
    },
  });

  // Simulate Mutation
  const simulateMutation = useMutation({
    mutationFn: ({ id, punchTime }: { id: string; punchTime: string }) =>
      attendanceApi.simulatePolicy(id, {
        punch_time: `${new Date().toISOString().split("T")[0]}T${punchTime}:00Z`,
        punch_type: "checkin",
      }),
    onSuccess: (data: unknown) => {
      setSimulationResult(data as Record<string, unknown>);
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError((err as Error).message || "Simulation failed.");
    },
  });

  const policies = policiesData?.results ?? [];

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
              {t("attendance.policiesTitle", "Attendance Policies, Shifts & Grace Rules")}
            </h1>
            <p className="text-xs text-slate-500">
              {t(
                "attendance.policiesSubtitle",
                "Configure shift timings, arrival grace windows, auto-absent cutoffs, and run simulator tests."
              )}
            </p>
          </div>
        </div>

        <Button
          onClick={() => {
            reset();
            setShowAddModal(true);
          }}
          className="gap-2 bg-emerald-800 text-xs hover:bg-emerald-900 text-white rounded-lg h-9 shadow-xs"
        >
          <Plus className="h-4 w-4" />
          <span>{t("attendance.addPolicy", "Create Policy")}</span>
        </Button>
      </div>

      {/* Policy Cards Grid */}
      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
        </div>
      ) : policies.length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-500 rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          {t("attendance.noPolicies", "No attendance policies created yet.")}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {policies.map((p) => (
            <div
              key={p.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{p.name}</h3>
                    <span
                      className={`rounded-md px-1.5 py-0.2 text-[10px] font-bold uppercase ${
                        p.is_active
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                          : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                      }`}
                    >
                      {p.is_active ? "Active" : "Disabled"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 capitalize pt-0.5">
                    Target: <span className="font-semibold text-slate-700 dark:text-slate-300">{p.user_type}</span>
                    {p.shift_name ? ` • Shift: ${p.shift_name}` : ""}
                  </p>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSimulatingPolicy(p);
                    setSimulationResult(null);
                    setSimulationPunchTime(p.start_time ? p.start_time.slice(0, 5) : "08:10");
                  }}
                  className="h-7 px-2 text-[11px] text-emerald-700 hover:bg-emerald-50 border-emerald-300"
                >
                  <Play className="h-3 w-3 mr-1" />
                  Test Simulator
                </Button>
              </div>

              {/* Timing Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Shift Timing</span>
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                    {p.start_time?.slice(0, 5)} - {p.end_time?.slice(0, 5)}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Grace Window</span>
                  <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">
                    +{p.grace_minutes ?? 15} mins
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Late Cutoff</span>
                  <span className="font-mono font-bold text-amber-700 dark:text-amber-400">
                    +{p.late_threshold_minutes ?? 30} mins
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Half-Day</span>
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                    +{p.half_day_threshold_minutes ?? 120} mins
                  </span>
                </div>
              </div>

              {/* Weekend config */}
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Calendar className="h-3.5 w-3.5 text-slate-400" />
                <span>
                  Configured Weekends:{" "}
                  <span className="font-semibold text-slate-700 dark:text-slate-300 capitalize">
                    {Array.isArray(p.weekend_days) ? p.weekend_days.join(", ") : "Friday, Saturday"}
                  </span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Simulator Modal */}
      {simulatingPolicy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Sliders className="h-4 w-4 text-emerald-700" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Punch Evaluation Simulator
                </h2>
              </div>
              <button onClick={() => setSimulatingPolicy(null)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Test how <span className="font-semibold text-slate-900 dark:text-slate-100">{simulatingPolicy.name}</span> evaluates a biometric punch timestamp against start time ({simulatingPolicy.start_time?.slice(0, 5)}) and grace period.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label htmlFor="sim-punch-time" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Test Arrival Punch Time (HH:MM)</label>
                <Input
                  id="sim-punch-time"
                  type="time"
                  value={simulationPunchTime}
                  onChange={(e) => setSimulationPunchTime(e.target.value)}
                  className="h-9 text-xs font-mono"
                />
              </div>

              <Button
                size="sm"
                disabled={simulateMutation.isPending}
                onClick={() =>
                  simulateMutation.mutate({
                    id: simulatingPolicy.id,
                    punchTime: simulationPunchTime,
                  })
                }
                className="w-full bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {simulateMutation.isPending ? "Simulating..." : "Evaluate Status"}
              </Button>
            </div>

            {simulationResult && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 dark:border-emerald-900/50 dark:bg-emerald-950/40 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-emerald-950 dark:text-emerald-200">Evaluated Outcome:</span>
                  <span className="font-mono font-bold uppercase text-emerald-800 dark:text-emerald-300">
                    {typeof simulationResult.status === "string"
                      ? simulationResult.status
                      : "Calculated"}
                  </span>
                </div>
                <div className="text-[11px] text-slate-600 dark:text-slate-400 font-mono">
                  Late minutes:{" "}
                  {typeof simulationResult.minutes_late === "number"
                    ? simulationResult.minutes_late
                    : 0}
                  m
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Add Policy */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Create Attendance & Shift Policy
              </h2>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>

            {actionError && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <form
              onSubmit={(e) => {
                void handleSubmit((data) => createPolicyMutation.mutate(data))(e);
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label htmlFor="policy-name" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Policy Name *</label>
                <Input id="policy-name" {...register("name")} placeholder="e.g. Regular Morning Shift" className="h-9 text-xs" />
                {errors.name && <p className="mt-1 text-[11px] text-rose-600">{errors.name.message}</p>}
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label htmlFor="policy-user-type" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Target Type *</label>
                  <select
                    id="policy-user-type"
                    {...register("user_type")}
                    className="w-full h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="student">Student</option>
                    <option value="staff">Staff</option>
                    <option value="all">Both</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="policy-start-time" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Shift Start *</label>
                  <Input id="policy-start-time" type="time" {...register("start_time")} className="h-9 text-xs font-mono" />
                </div>

                <div>
                  <label htmlFor="policy-end-time" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Shift End *</label>
                  <Input id="policy-end-time" type="time" {...register("end_time")} className="h-9 text-xs font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label htmlFor="policy-grace-mins" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Grace Window (Mins)</label>
                  <Input id="policy-grace-mins" type="number" {...register("grace_minutes")} className="h-9 text-xs font-mono" />
                </div>

                <div>
                  <label htmlFor="policy-late-mins" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Late Cutoff (Mins)</label>
                  <Input id="policy-late-mins" type="number" {...register("late_threshold_minutes")} className="h-9 text-xs font-mono" />
                </div>

                <div>
                  <label htmlFor="policy-half-day-mins" className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">Half-Day (Mins)</label>
                  <Input id="policy-half-day-mins" type="number" {...register("half_day_threshold_minutes")} className="h-9 text-xs font-mono" />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setShowAddModal(false)}>
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isSubmitting || createPolicyMutation.isPending}
                  className="bg-emerald-800 hover:bg-emerald-900 text-white"
                >
                  {isSubmitting ? "Saving..." : "Save Policy"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
