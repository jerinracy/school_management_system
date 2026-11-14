import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths, components } from "@/types/api";

export type StaffListItem = paths["/api/v1/staff/staff/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type StaffDetail = paths["/api/v1/staff/staff/{id}/"]["get"]["responses"]["200"]["content"]["application/json"];
export type StaffCreateInput = components["schemas"]["StaffCreateUpdateRequest"];
export type DepartmentItem = paths["/api/v1/staff/departments/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type DepartmentCreateInput = components["schemas"]["DepartmentRequest"];
export type DesignationItem = paths["/api/v1/staff/designations/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type DesignationCreateInput = components["schemas"]["DesignationRequest"];
export type LeaveTypeItem = paths["/api/v1/staff/leave-types/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type LeaveBalanceItem = paths["/api/v1/staff/leave-balances/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type LeaveRequestItem = paths["/api/v1/staff/leave-requests/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type TeacherAssignmentItem = paths["/api/v1/staff/teacher-assignments/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];

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

export const staffApi = {
  // Staff Directory
  async getStaffList(params?: {
    search?: string;
    department?: string;
    designation?: string;
    staff_type?: string;
    status?: string;
    is_mpo?: boolean;
    page?: number;
    ordering?: string;
  }) {
    const res = await apiClient.GET("/api/v1/staff/staff/", {
      params: {
        query: {
          search: params?.search,
          department: params?.department,
          designation: params?.designation,
          staff_type: params?.staff_type as never,
          status: params?.status as never,
          is_mpo: params?.is_mpo,
          page: params?.page,
          ordering: params?.ordering,
        },
      },
    });
    return checkResponse(res);
  },

  async getStaff(id: string) {
    const res = await apiClient.GET("/api/v1/staff/staff/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async createStaff(data: StaffCreateInput) {
    const res = await apiClient.POST("/api/v1/staff/staff/", {
      body: data,
    });
    return checkResponse(res);
  },

  async updateStaff(id: string, data: Partial<StaffCreateInput>) {
    const res = await apiClient.PATCH("/api/v1/staff/staff/{id}/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  async deleteStaff(id: string) {
    const res = await apiClient.DELETE("/api/v1/staff/staff/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  // Departments
  async getDepartments(params?: { search?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/staff/departments/", {
      params: {
        query: {
          search: params?.search,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async createDepartment(data: DepartmentCreateInput) {
    const res = await apiClient.POST("/api/v1/staff/departments/", {
      body: data,
    });
    return checkResponse(res);
  },

  // Designations
  async getDesignations(params?: { search?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/staff/designations/", {
      params: {
        query: {
          search: params?.search,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async createDesignation(data: DesignationCreateInput) {
    const res = await apiClient.POST("/api/v1/staff/designations/", {
      body: data,
    });
    return checkResponse(res);
  },

  // Leaves
  async getLeaveTypes() {
    const res = await apiClient.GET("/api/v1/staff/leave-types/", {});
    return checkResponse(res);
  },

  async getLeaveBalances(params?: { staff?: string; session?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/staff/leave-balances/", {
      params: {
        query: {
          staff: params?.staff,
          session: params?.session,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async getLeaveRequests(params?: {
    staff?: string;
    leave_type?: string;
    session?: string;
    status?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/staff/leave-requests/", {
      params: {
        query: {
          staff: params?.staff,
          leave_type: params?.leave_type,
          session: params?.session,
          status: params?.status as never,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async applyLeave(data: {
    staff_id?: string;
    leave_type_id: string;
    session_id?: string;
    start_date: string;
    end_date: string;
    reason: string;
    emergency_contact_phone?: string;
  }) {
    const res = await apiClient.POST("/api/v1/staff/leave-requests/", {
      body: data as never,
    });
    return checkResponse(res);
  },

  async approveLeave(id: string, notes?: string) {
    const res = await apiClient.POST("/api/v1/staff/leave-requests/{id}/approve/", {
      params: { path: { id } },
      body: { notes: notes || "" } as never,
    });
    return checkResponse(res);
  },

  async rejectLeave(id: string, rejectionReason: string) {
    const res = await apiClient.POST("/api/v1/staff/leave-requests/{id}/reject/", {
      params: { path: { id } },
      body: { rejection_reason: rejectionReason } as never,
    });
    return checkResponse(res);
  },

  // Teacher Assignments
  async getTeacherAssignments(params?: {
    teacher?: string;
    session?: string;
    class_level?: string;
    section?: string;
    subject?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/staff/teacher-assignments/", {
      params: {
        query: {
          teacher: params?.teacher,
          session: params?.session,
          class_level: params?.class_level,
          section: params?.section,
          subject: params?.subject,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  getExportUrl() {
    return "/api/v1/staff/staff/export/";
  },

  getIdCardPdfUrl(staffId: string) {
    return `/api/v1/staff/staff/${staffId}/id-card/?download=pdf`;
  },
};
