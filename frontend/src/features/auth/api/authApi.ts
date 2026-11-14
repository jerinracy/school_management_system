import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths } from "@/types/api";

export interface LoginSuccessPayload {
  access: string;
  refresh: string;
  user: {
    id: string;
    username: string;
    full_name: string;
    phone: string;
    email: string;
    user_type: string;
    institution_id: string | null;
    roles: string[];
    permissions?: string[];
    must_change_password?: boolean;
    language_preference?: string;
  };
}

export interface TotpRequiredPayload {
  code: "TOTP_REQUIRED";
  message: string;
  user_id: string;
}

export type LoginResult = LoginSuccessPayload | TotpRequiredPayload;

export type LoginRequest = paths["/api/v1/auth/login/"]["post"]["requestBody"]["content"]["application/json"];
export type OtpRequest = paths["/api/v1/auth/otp/request/"]["post"]["requestBody"]["content"]["application/json"];
export type OtpVerifyRequest = paths["/api/v1/auth/otp/verify/"]["post"]["requestBody"]["content"]["application/json"];
export type PasswordChangeRequest = paths["/api/v1/auth/password/change/"]["post"]["requestBody"]["content"]["application/json"];
export type UserProfileResponse = paths["/api/v1/auth/me/"]["get"]["responses"]["200"]["content"]["application/json"];

export interface UserProfilePatch {
  full_name?: string;
  email?: string | null;
  language_preference?: "en" | "bn";
  avatar?: string | null;
}

function throwNormalizedError(response: Response, error: unknown): never {
  throw parseApiError(response.status, error);
}

export const authApi = {
  async login(payload: Partial<LoginRequest> & { identifier: string; password: string }): Promise<LoginResult> {
    const fullPayload: LoginRequest = {
      identifier: payload.identifier,
      password: payload.password,
      device_id: payload.device_id ?? "web-dashboard",
      device_name: payload.device_name ?? "Web Browser",
      platform: payload.platform ?? "web",
      app_version: payload.app_version ?? "0.1.0",
      fcm_token: payload.fcm_token ?? "",
    };

    const { data, error, response } = await apiClient.POST("/api/v1/auth/login/", {
      body: fullPayload,
    });
    if (error) throwNormalizedError(response, error);
    return data as unknown as LoginResult;
  },

  async requestOtp(payload: OtpRequest) {
    const { data, error, response } = await apiClient.POST("/api/v1/auth/otp/request/", {
      body: payload,
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async verifyOtp(payload: Partial<OtpVerifyRequest> & { phone: string; code: string }): Promise<LoginSuccessPayload> {
    const fullPayload: OtpVerifyRequest = {
      phone: payload.phone,
      code: payload.code,
      purpose: payload.purpose ?? "login",
      device_id: payload.device_id ?? "web-dashboard",
      platform: payload.platform ?? "web",
    };

    const { data, error, response } = await apiClient.POST("/api/v1/auth/otp/verify/", {
      body: fullPayload,
    });
    if (error) throwNormalizedError(response, error);
    return data as unknown as LoginSuccessPayload;
  },

  async refresh(refresh: string): Promise<{ access: string; refresh: string }> {
    const { data, error, response } = await apiClient.POST("/api/v1/auth/refresh/", {
      body: { refresh },
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async logout(refresh: string) {
    const { data, error, response } = await apiClient.POST("/api/v1/auth/logout/", {
      body: { refresh } as never,
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async logoutAll() {
    const { data, error, response } = await apiClient.POST("/api/v1/auth/logout-all/", {
      body: {} as never,
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async changePassword(payload: PasswordChangeRequest) {
    const { data, error, response } = await apiClient.POST("/api/v1/auth/password/change/", {
      body: payload,
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async getMe(): Promise<UserProfileResponse> {
    const { data, error, response } = await apiClient.GET("/api/v1/auth/me/");
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async updateMe(payload: UserProfilePatch): Promise<UserProfileResponse> {
    const { data, error, response } = await apiClient.PATCH("/api/v1/auth/me/", {
      body: payload as never,
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async getSessions() {
    const { data, error, response } = await apiClient.GET("/api/v1/auth/sessions/");
    if (error) throwNormalizedError(response, error);
    return data;
  },

  async revokeSession(id: string) {
    const { data, error, response } = await apiClient.POST("/api/v1/auth/sessions/{id}/revoke/", {
      params: { path: { id } },
    });
    if (error) throwNormalizedError(response, error);
    return data;
  },
};
