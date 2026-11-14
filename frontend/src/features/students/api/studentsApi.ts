import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths, components } from "@/types/api";

export type StudentListItem = paths["/api/v1/students/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type StudentDetail = paths["/api/v1/students/{id}/"]["get"]["responses"]["200"]["content"]["application/json"];
export type StudentCreateInput = components["schemas"]["StudentCreateUpdateRequest"];
export type StudentEnrollmentItem = paths["/api/v1/students/enrollments/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type StudentEnrollmentInput = components["schemas"]["StudentEnrollmentCreateUpdateRequest"];
export type GuardianItem = paths["/api/v1/guardians/guardians/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type GuardianCreateInput = components["schemas"]["GuardianRequest"];
export type LinkStudentInput = components["schemas"]["LinkStudentActionRequest"];

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

export const studentsApi = {
  async getStudents(params?: {
    search?: string;
    gender?: string;
    religion?: string;
    blood_group?: string;
    status?: string;
    page?: number;
    ordering?: string;
  }) {
    const res = await apiClient.GET("/api/v1/students/", {
      params: {
        query: {
          search: params?.search,
          gender: params?.gender as never,
          religion: params?.religion as never,
          blood_group: params?.blood_group as never,
          status: params?.status as never,
          page: params?.page,
          ordering: params?.ordering,
        },
      },
    });
    return checkResponse(res);
  },

  async getStudent(id: string) {
    const res = await apiClient.GET("/api/v1/students/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async createStudent(data: StudentCreateInput) {
    const res = await apiClient.POST("/api/v1/students/", {
      body: data,
    });
    return checkResponse(res);
  },

  async updateStudent(id: string, data: Partial<StudentCreateInput>) {
    const res = await apiClient.PATCH("/api/v1/students/{id}/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  async deleteStudent(id: string) {
    const res = await apiClient.DELETE("/api/v1/students/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async getEnrollments(params?: {
    student?: string;
    session?: string;
    class_level?: string;
    section?: string;
    status?: string;
    page?: number;
    ordering?: string;
  }) {
    const res = await apiClient.GET("/api/v1/students/enrollments/", {
      params: {
        query: {
          student: params?.student,
          session: params?.session,
          class_level: params?.class_level,
          section: params?.section,
          status: params?.status as never,
          page: params?.page,
          ordering: params?.ordering,
        },
      },
    });
    return checkResponse(res);
  },

  async createEnrollment(data: StudentEnrollmentInput) {
    const res = await apiClient.POST("/api/v1/students/enrollments/", {
      body: data,
    });
    return checkResponse(res);
  },

  async autoAssignRolls(data: {
    session_id: string;
    section_id: string;
    strategy?: "name_en" | "name_bn" | "student_id";
  }) {
    const res = await apiClient.POST("/api/v1/students/enrollments/auto-assign-rolls/", {
      body: data as never,
    });
    return checkResponse(res);
  },

  async getGuardians(params?: { search?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/guardians/guardians/", {
      params: {
        query: {
          search: params?.search,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async createGuardian(data: GuardianCreateInput) {
    const res = await apiClient.POST("/api/v1/guardians/guardians/", {
      body: data,
    });
    return checkResponse(res);
  },

  async linkGuardian(guardianId: string, data: LinkStudentInput) {
    const res = await apiClient.POST("/api/v1/guardians/guardians/{id}/link-student/", {
      params: { path: { id: guardianId } },
      body: data,
    });
    return checkResponse(res);
  },

  async unlinkGuardian(guardianId: string, studentId: string) {
    const res = await apiClient.POST("/api/v1/guardians/guardians/{id}/unlink-student/", {
      params: { path: { id: guardianId } },
      body: { student_id: studentId },
    });
    return checkResponse(res);
  },

  async createGuardianPortalAccount(guardianId: string) {
    const res = await apiClient.POST(
      "/api/v1/guardians/guardians/{id}/create-portal-account/",
      {
        params: { path: { id: guardianId } },
        body: {} as never,
      },
    );
    return checkResponse(res);
  },

  getExportUrl() {
    return "/api/v1/students/export/";
  },

  getIdCardPdfUrl(studentId: string) {
    return `/api/v1/students/${studentId}/id-card/?download=pdf`;
  },
};
