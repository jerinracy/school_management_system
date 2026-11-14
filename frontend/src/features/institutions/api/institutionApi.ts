import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths } from "@/types/api";

export type InstitutionProfile = paths["/api/v1/institutions/profile/"]["get"]["responses"]["200"]["content"]["application/json"];
export type InstitutionPublicBranding = paths["/api/v1/institutions/public-branding/"]["get"]["responses"]["200"]["content"]["application/json"];
export type Branch = paths["/api/v1/institutions/branches/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Shift = paths["/api/v1/institutions/shifts/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type AcademicSession = paths["/api/v1/institutions/sessions/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Term = paths["/api/v1/institutions/terms/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Holiday = paths["/api/v1/institutions/holidays/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];

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

export const institutionApi = {
  async getPublicBranding(params?: { eiin?: string; institution_id?: string }): Promise<InstitutionPublicBranding> {
    const res = await apiClient.GET("/api/v1/institutions/public-branding/", {
      params: params ? { query: params } : undefined,
    });
    return checkResponse(res);
  },

  async getProfile(): Promise<InstitutionProfile> {
    const res = await apiClient.GET("/api/v1/institutions/profile/");
    return checkResponse(res);
  },

  async updateProfile(formData: FormData | Record<string, unknown>): Promise<InstitutionProfile> {
    const isFormData = typeof FormData !== "undefined" && formData instanceof FormData;
    const body = isFormData ? formData : (formData as never);
    const res = await apiClient.PATCH("/api/v1/institutions/profile/", {
      body: body as never,
    });
    return checkResponse(res);
  },

  async getBranches() {
    const res = await apiClient.GET("/api/v1/institutions/branches/");
    return checkResponse(res).results ?? [];
  },

  async createBranch(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/institutions/branches/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteBranch(id: string) {
    const res = await apiClient.DELETE("/api/v1/institutions/branches/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async getShifts() {
    const res = await apiClient.GET("/api/v1/institutions/shifts/");
    return checkResponse(res).results ?? [];
  },

  async createShift(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/institutions/shifts/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteShift(id: string) {
    const res = await apiClient.DELETE("/api/v1/institutions/shifts/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async getSessions() {
    const res = await apiClient.GET("/api/v1/institutions/sessions/");
    return checkResponse(res).results ?? [];
  },

  async createSession(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/institutions/sessions/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async activateSession(id: string) {
    const res = await apiClient.POST("/api/v1/institutions/sessions/{id}/activate/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async closeSession(id: string) {
    const res = await apiClient.POST("/api/v1/institutions/sessions/{id}/close/", {
      params: { path: { id } },
      body: { confirm: true },
    });
    return checkResponse(res);
  },

  async getTerms(sessionId?: string) {
    const res = await apiClient.GET("/api/v1/institutions/terms/", {
      params: sessionId ? { query: { session: sessionId } } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createTerm(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/institutions/terms/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteTerm(id: string) {
    const res = await apiClient.DELETE("/api/v1/institutions/terms/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async getHolidays() {
    const res = await apiClient.GET("/api/v1/institutions/holidays/");
    return checkResponse(res).results ?? [];
  },

  async createHoliday(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/institutions/holidays/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteHoliday(id: string) {
    const res = await apiClient.DELETE("/api/v1/institutions/holidays/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },
};
