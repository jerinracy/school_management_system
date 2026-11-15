import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths, components } from "@/types/api";

export type DeviceItem = paths["/api/v1/devices/terminals/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type DeviceCreateInput = components["schemas"]["DeviceRequest"];
export type RawPunchItem = paths["/api/v1/devices/punches/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type DeviceCommandItem = paths["/api/v1/devices/commands/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type DeviceUserMapItem = paths["/api/v1/devices/user-maps/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];

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

export const devicesApi = {
  // Terminals / Hardware Inventory
  async getTerminals(params?: {
    search?: string;
    branch?: string;
    status?: string;
    is_active?: boolean;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/devices/terminals/", {
      params: {
        query: {
          search: params?.search,
          branch: params?.branch,
          status: params?.status as never,
          is_active: params?.is_active,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async getTerminal(id: string) {
    const res = await apiClient.GET("/api/v1/devices/terminals/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async createTerminal(data: DeviceCreateInput) {
    const res = await apiClient.POST("/api/v1/devices/terminals/", {
      body: data,
    });
    return checkResponse(res);
  },

  async updateTerminal(id: string, data: Partial<DeviceCreateInput>) {
    const res = await apiClient.PATCH("/api/v1/devices/terminals/{id}/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  async deleteTerminal(id: string) {
    const res = await apiClient.DELETE("/api/v1/devices/terminals/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async testConnection(id: string) {
    const res = await apiClient.POST("/api/v1/devices/terminals/{id}/test-connection/", {
      params: { path: { id } },
      body: {} as never,
    });
    return checkResponse(res);
  },

  // Raw Punch Logs
  async getRawPunches(params?: {
    device?: string;
    status?: string;
    search?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/devices/punches/", {
      params: {
        query: {
          device: params?.device,
          status: params?.status as never,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  // Unmapped Punches
  async getUnmappedPunches(params?: { page?: number }) {
    const res = await apiClient.GET("/api/v1/devices/unmapped-punches/", {
      params: { query: { page: params?.page } },
    });
    return checkResponse(res);
  },

  async resolveUnmappedPunch(
    id: string,
    data: { student_id?: string; staff_id?: string }
  ) {
    const res = await apiClient.POST("/api/v1/devices/unmapped-punches/{id}/resolve/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  // Device Commands
  async getCommands(params?: { device?: string; status?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/devices/commands/", {
      params: {
        query: {
          device: params?.device,
          status: params?.status as never,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async queueCommand(
    id: string,
    data: { command_type: string; payload?: Record<string, unknown> }
  ) {
    const res = await apiClient.POST("/api/v1/devices/terminals/{id}/queue-command/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse(res);
  },

  // User Device Mappings
  async getUserMaps(params?: { search?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/devices/user-maps/", {
      params: { query: { search: params?.search, page: params?.page } },
    });
    return checkResponse(res);
  },
};
