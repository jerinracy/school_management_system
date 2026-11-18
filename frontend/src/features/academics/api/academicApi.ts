import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths } from "@/types/api";

export type ClassLevel = paths["/api/v1/academics/classes/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type AcademicGroup = paths["/api/v1/academics/groups/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Section = paths["/api/v1/academics/sections/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Subject = paths["/api/v1/academics/subjects/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type ClassSubject = paths["/api/v1/academics/class-subjects/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Period = paths["/api/v1/academics/periods/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Room = paths["/api/v1/academics/rooms/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type RoutineSlot = paths["/api/v1/academics/routine/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type Substitute = paths["/api/v1/academics/substitutes/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];

export interface RoutineValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings?: string[];
  conflicts?: Array<{ type: string; message: string }>;
}

export interface CopySessionResult {
  success: boolean;
  dry_run: boolean;
  source_session: string;
  target_session: string;
  sections_created: number;
  sections_skipped: number;
  class_subjects_created: number;
  class_subjects_skipped: number;
}

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

export const academicApi = {
  async getClasses(params?: { shift?: string; session?: string; branch?: string }) {
    const res = await apiClient.GET("/api/v1/academics/classes/", {
      params: params ? { query: params as never } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createClass(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/classes/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getGroups() {
    const res = await apiClient.GET("/api/v1/academics/groups/");
    return checkResponse(res).results ?? [];
  },

  async getSections(queryOrClassId?: string | { class_level?: string; shift?: string; session?: string; branch?: string }) {
    const query = typeof queryOrClassId === "string" ? { class_level: queryOrClassId } : queryOrClassId;
    const res = await apiClient.GET("/api/v1/academics/sections/", {
      params: query ? { query: query as never } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createSection(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/sections/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async bulkCreateSections(payload: {
    class_id: string;
    names: string[];
    shift_id?: string;
    session_id?: string;
    class_level_id?: string;
    capacity?: number;
  }) {
    const res = await apiClient.POST("/api/v1/academics/sections/bulk-create/", {
      body: {
        ...payload,
        class_level_id: payload.class_level_id || payload.class_id,
      } as never,
    });
    return checkResponse(res);
  },

  async getSubjects() {
    const res = await apiClient.GET("/api/v1/academics/subjects/");
    return checkResponse(res).results ?? [];
  },

  async createSubject(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/subjects/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getClassSubjects(classId?: string) {
    const res = await apiClient.GET("/api/v1/academics/class-subjects/", {
      params: classId ? { query: { class_level: classId } } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createClassSubject(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/class-subjects/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getPeriods(params?: { shift?: string }) {
    const res = await apiClient.GET("/api/v1/academics/periods/", {
      params: params ? { query: params as never } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createPeriod(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/periods/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getRooms(params?: { branch?: string }) {
    const res = await apiClient.GET("/api/v1/academics/rooms/", {
      params: params ? { query: params as never } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createRoom(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/rooms/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getRoutine(params?: string | { section?: string; weekday?: number }) {
    const query = typeof params === "string" ? { section: params } : params;
    const res = await apiClient.GET("/api/v1/academics/routine/", {
      params: query ? { query: query as never } : undefined,
    });
    return checkResponse(res).results ?? [];
  },

  async createRoutineSlot(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/routine/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async updateRoutineSlot(id: string, payload: Record<string, unknown>) {
    const res = await apiClient.PATCH("/api/v1/academics/routine/{id}/", {
      params: { path: { id } },
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteRoutineSlot(id: string) {
    const res = await apiClient.DELETE("/api/v1/academics/routine/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async validateRoutineSlot(payload: Record<string, unknown>): Promise<RoutineValidationResult> {
    const res = await apiClient.POST("/api/v1/academics/routine/validate/", {
      body: payload as never,
    });
    return checkResponse(res) as unknown as RoutineValidationResult;
  },

  async getSubstitutes() {
    const res = await apiClient.GET("/api/v1/academics/substitutes/");
    return checkResponse(res).results ?? [];
  },

  async createSubstitute(payload: Record<string, unknown>) {
    const res = await apiClient.POST("/api/v1/academics/substitutes/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteSubstitute(id: string) {
    const res = await apiClient.DELETE("/api/v1/academics/substitutes/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async copySession(payload: { source_session_id: string; target_session_id: string; dry_run?: boolean }): Promise<CopySessionResult> {
    const res = await apiClient.POST("/api/v1/academics/copy-session/", {
      body: payload as never,
    });
    return checkResponse(res) as unknown as CopySessionResult;
  },
};
