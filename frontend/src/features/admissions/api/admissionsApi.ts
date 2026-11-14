import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths, components } from "@/types/api";

export type CircularListItem = paths["/api/v1/admissions/circulars/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type ApplicationListItem = paths["/api/v1/admissions/applications/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type CircularCreateInput = components["schemas"]["AdmissionCircular"];

function checkResponse<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

export const admissionsApi = {
  async getCirculars(params?: { status?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/admissions/circulars/", {
      params: {
        query: {
          status: params?.status as never,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async getCircular(id: string) {
    const res = await apiClient.GET("/api/v1/admissions/circulars/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async createCircular(data: CircularCreateInput) {
    const res = await apiClient.POST("/api/v1/admissions/circulars/", {
      body: data,
    });
    return checkResponse(res);
  },

  async publishCircular(id: string) {
    const res = await apiClient.POST("/api/v1/admissions/circulars/{id}/publish/", {
      params: { path: { id } },
      body: {} as never,
    });
    return checkResponse(res);
  },

  async closeCircular(id: string) {
    const res = await apiClient.POST("/api/v1/admissions/circulars/{id}/close/", {
      params: { path: { id } },
      body: {} as never,
    });
    return checkResponse(res);
  },

  async getApplications(params?: {
    circular?: string;
    status?: string;
    search?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/admissions/applications/", {
      params: {
        query: {
          circular: params?.circular,
          status: params?.status as never,
          search: params?.search,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async transitionApplication(id: string, newStatus: string, reason?: string) {
    const res = await apiClient.POST(
      "/api/v1/admissions/applications/{id}/transition/",
      {
        params: { path: { id } },
        body: { new_status: newStatus, notes: reason || "" } as never,
      },
    );
    return checkResponse(res);
  },

  async convertToStudent(
    applicationId: string,
    data: { section_id: string; roll_no: number; session_id?: string },
  ) {
    const res = await apiClient.POST(
      "/api/v1/admissions/applications/{id}/convert-to-student/",
      {
        params: { path: { id: applicationId } },
        body: data as never,
      },
    );
    return checkResponse(res);
  },

  async runLotteryDraw(data: { circular_id: string; seed?: number }) {
    const res = await apiClient.POST("/api/v1/admissions/lottery/draw/", {
      body: {
        circular_id: data.circular_id,
        total_to_select: 50,
        seed: data.seed ?? null,
        auto_advance_status: true,
      } as never,
    });
    return checkResponse(res);
  },

  async generateMeritList(data: { circular_id: string }) {
    const res = await apiClient.POST("/api/v1/admissions/merit-lists/generate/", {
      body: {
        circular_id: data.circular_id,
        selection_criteria: "gpa",
        title: "Merit List",
        auto_publish: false,
      } as never,
    });
    return checkResponse(res);
  },
};
