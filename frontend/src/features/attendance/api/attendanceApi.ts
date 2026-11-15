import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths, components } from "@/types/api";

export type DailyAttendanceItem = paths["/api/v1/attendance/daily/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type AttendanceCorrectionItem = paths["/api/v1/attendance/corrections/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type PeriodAttendanceItem = paths["/api/v1/attendance/periods/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type AttendancePolicyItem = paths["/api/v1/attendance/policies/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type AttendancePolicyInput = components["schemas"]["AttendancePolicyRequest"];

function checkResponse<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

function checkVoid(res: { error?: unknown; response: Response }): void {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
}

export const attendanceApi = {
  // Daily Attendance
  async getDailyAttendance(params?: {
    date?: string;
    user_type?: "student" | "staff" | "all";
    status?: string;
    student?: string;
    staff?: string;
    search?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/attendance/daily/", {
      params: {
        query: {
          date: params?.date,
          user_type: params?.user_type as never,
          status: params?.status as never,
          student: params?.student,
          staff: params?.staff,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async bulkManualAttendance(data: {
    date: string;
    user_type: "student" | "staff";
    records: Array<{
      student_id?: string;
      staff_id?: string;
      status: "present" | "late" | "absent" | "half_day" | "leave" | "holiday";
      remarks?: string;
    }>;
  }) {
    const res = await apiClient.POST("/api/v1/attendance/daily/bulk-manual/", {
      body: data as never,
    });
    return checkResponse(res);
  },

  async recomputeAttendance(data: {
    start_date: string;
    end_date: string;
    user_type?: "student" | "staff" | "all";
  }) {
    const res = await apiClient.POST("/api/v1/attendance/daily/recompute/", {
      body: data as never,
    });
    return checkResponse(res);
  },

  // Attendance Corrections
  async getCorrections(params?: {
    approval_status?: "pending" | "approved" | "rejected";
    target_date?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/attendance/corrections/", {
      params: {
        query: {
          approval_status: params?.approval_status as never,
          target_date: params?.target_date,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async decideCorrection(
    id: string,
    data: { approved: boolean; rejection_reason?: string }
  ) {
    const res = await apiClient.POST("/api/v1/attendance/corrections/{id}/decide/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  // Period-by-Period Classroom Attendance
  async getPeriodAttendance(params?: {
    date?: string;
    section?: string;
    routine_slot?: string;
    subject?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/attendance/periods/", {
      params: {
        query: {
          date: params?.date,
          section: params?.section,
          routine_slot: params?.routine_slot,
          subject: params?.subject,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async bulkSubmitPeriodAttendance(data: {
    date: string;
    section: string;
    routine_slot?: string;
    subject: string;
    records: Array<{
      student_id: string;
      status: "present" | "absent" | "late" | "excused";
      remarks?: string;
    }>;
  }) {
    const res = await apiClient.POST("/api/v1/attendance/periods/bulk-submit/", {
      body: data as never,
    });
    return checkResponse(res);
  },

  // Policies
  async getPolicies() {
    const res = await apiClient.GET("/api/v1/attendance/policies/", {});
    return checkResponse(res);
  },

  async createPolicy(data: AttendancePolicyInput) {
    const res = await apiClient.POST("/api/v1/attendance/policies/", {
      body: data,
    });
    return checkResponse(res);
  },

  async updatePolicy(id: string, data: Partial<AttendancePolicyInput>) {
    const res = await apiClient.PATCH("/api/v1/attendance/policies/{id}/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  async deletePolicy(id: string) {
    const res = await apiClient.DELETE("/api/v1/attendance/policies/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async simulatePolicy(id: string, data: { punch_time: string; punch_type: string }) {
    const res = await apiClient.POST("/api/v1/attendance/policies/{id}/simulate/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },
};
