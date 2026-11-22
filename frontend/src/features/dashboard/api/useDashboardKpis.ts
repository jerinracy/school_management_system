import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface HeadcountKpis {
  total_teachers: number;
  total_office_staff: number;
  total_students: number;
  morning_shift_students: number;
  day_shift_students: number;
  total_classes: number;
  total_sections: number;
}

export interface AttendanceSummary {
  student: Record<string, number>;
  staff: Record<string, number>;
}

export interface AttendanceRates {
  student_present_pct: number;
  staff_present_pct: number;
}

export interface DeviceStatusSummary {
  online?: number;
  offline?: number;
  maintenance?: number;
  error?: number;
  [key: string]: number | undefined;
}

export interface DashboardKpisResponse {
  date: string;
  role_variant: string;
  headcount: HeadcountKpis;
  attendance: AttendanceSummary;
  attendance_rates: AttendanceRates;
  devices: DeviceStatusSummary;
  upcoming_exams_count: number;
  pending_approvals: {
    attendance_corrections: number;
  };
  finance?: {
    currency: string;
    collected_today: string;
    total_outstanding_dues: string;
  };
}

export async function fetchDashboardKpis(targetDate?: string): Promise<DashboardKpisResponse> {
  const res = targetDate
    ? await apiClient.GET("/api/v1/reports/dashboard/kpis/", {
        params: { query: { date: targetDate } },
      })
    : await apiClient.GET("/api/v1/reports/dashboard/kpis/");

  if (res.error || !res.response.ok || !res.data) {
    throw new Error(`Failed to fetch dashboard KPIs: ${res.response?.status}`);
  }
  return res.data as unknown as DashboardKpisResponse;
}

export function useDashboardKpis(targetDate?: string) {
  return useQuery({
    queryKey: ["reports", "dashboard-kpis", targetDate ?? "today"],
    queryFn: () => fetchDashboardKpis(targetDate),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}
