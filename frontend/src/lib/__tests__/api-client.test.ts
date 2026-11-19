import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/lib/errors";
import { useAuthStore } from "@/features/auth/store/authStore";
import { server } from "@/test/msw/server";

describe("apiClient", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    useAuthStore.getState().setIsRestoring(false);
  });

  it("injects Bearer token and Accept-Language into request headers", async () => {
    useAuthStore.getState().setTokens("test-jwt-access", "test-jwt-refresh");

    let capturedAuth: string | null = null;
    let capturedLang: string | null = null;
    let capturedReqId: string | null = null;

    server.use(
      http.get(/\/api\/v1\/auth\/me\/$/, ({ request }) => {
        capturedAuth = request.headers.get("Authorization");
        capturedLang = request.headers.get("Accept-Language");
        capturedReqId = request.headers.get("X-Request-ID");
        return HttpResponse.json({
          id: "u-1",
          username: "admin",
          full_name: "Admin",
          phone: "+8801700000000",
          email: "admin@example.com",
          user_type: "admin",
          institution_id: "inst-1",
          roles: ["Admin"],
          permissions: [],
        });
      }),
    );

    const { data } = await apiClient.GET("/api/v1/auth/me/");
    expect(data?.username).toBe("admin");
    expect(capturedAuth).toBe("Bearer test-jwt-access");
    expect(capturedLang).toMatch(/en|bn/);
    expect(capturedReqId).toBeTruthy();
  });

  it("executes single-flight 401 refresh when multiple concurrent requests encounter 401", async () => {
    useAuthStore.getState().setTokens("expired-access", "valid-refresh");

    let refreshCalls = 0;

    server.use(
      http.post(/\/api\/v1\/auth\/refresh\/$/, () => {
        refreshCalls++;
        return HttpResponse.json({
          access: "new-access-token",
          refresh: "new-refresh-token",
        });
      }),
      http.get(/\/api\/v1\/auth\/me\/$/, ({ request }) => {
        const auth = request.headers.get("Authorization");
        if (auth !== "Bearer new-access-token") {
          return HttpResponse.json({ code: "AUTHENTICATION_REQUIRED", message: "Token expired" }, { status: 401 });
        }
        return HttpResponse.json({
          id: "u-1",
          username: "refreshed-admin",
          full_name: "Admin",
          phone: "+8801700000000",
          email: "admin@example.com",
          user_type: "admin",
          institution_id: "inst-1",
          roles: ["Admin"],
          permissions: [],
        });
      }),
    );

    // Trigger 2 concurrent requests
    const [res1, res2] = await Promise.all([
      apiClient.GET("/api/v1/auth/me/"),
      apiClient.GET("/api/v1/auth/me/"),
    ]);

    expect(res1.data?.username).toBe("refreshed-admin");
    expect(res2.data?.username).toBe("refreshed-admin");

    // Exactly one refresh call must have occurred
    expect(refreshCalls).toBe(1);
    expect(useAuthStore.getState().accessToken).toBe("new-access-token");
    expect(useAuthStore.getState().refreshToken).toBe("new-refresh-token");
  });

  it("transparently retries mutating POST requests with body payload on 401 token refresh", async () => {
    useAuthStore.getState().setTokens("expired-access", "valid-refresh");

    let receivedPayload: unknown = null;
    let refreshCalls = 0;

    server.use(
      http.post(/\/api\/v1\/auth\/refresh\/$/, () => {
        refreshCalls++;
        return HttpResponse.json({
          access: "new-access-token",
          refresh: "new-refresh-token",
        });
      }),
      http.post(/\/api\/v1\/communications\/notices\/$/, async ({ request }) => {
        const auth = request.headers.get("Authorization");
        if (auth !== "Bearer new-access-token") {
          return HttpResponse.json({ code: "AUTHENTICATION_REQUIRED", message: "Token expired" }, { status: 401 });
        }
        receivedPayload = await request.json();
        return HttpResponse.json(
          {
            id: "notice-uuid-123",
            title_en: "Urgent Campus Notice",
            content_en: "Notice details",
            category: "general",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          { status: 201 },
        );
      }),
    );

    const postPayload = {
      title_en: "Urgent Campus Notice",
      content_en: "Notice details",
      category: "general" as const,
    };

    const res = await apiClient.POST("/api/v1/communications/notices/", {
      body: postPayload,
    });

    expect(refreshCalls).toBe(1);
    expect(useAuthStore.getState().accessToken).toBe("new-access-token");
    expect(res.data?.id).toBe("notice-uuid-123");
    expect(res.data?.title_en).toBe("Urgent Campus Notice");
    expect(receivedPayload).toEqual(postPayload);
  });

  it("clears auth tokens and logs out if refresh endpoint fails", async () => {
    useAuthStore.getState().setTokens("expired-access", "invalid-refresh");

    server.use(
      http.post(/\/api\/v1\/auth\/refresh\/$/, () => {
        return HttpResponse.json({ code: "TOKEN_INVALID", message: "Token is blacklisted" }, { status: 401 });
      }),
      http.get(/\/api\/v1\/auth\/me\/$/, () => {
        return HttpResponse.json({ code: "AUTHENTICATION_REQUIRED", message: "Token expired" }, { status: 401 });
      }),
    );

    await expect(apiClient.GET("/api/v1/auth/me/")).rejects.toThrow();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("maps error responses into typed ApiError with status and code", async () => {
    server.use(
      http.get(/\/api\/v1\/auth\/me\/$/, () => {
        return HttpResponse.json(
          {
            code: "PERMISSION_DENIED",
            message: "User lacks view permission",
            details: { reason: "Restricted role" },
          },
          { status: 403 },
        );
      }),
    );

    try {
      await apiClient.GET("/api/v1/auth/me/");
      expect.fail("Expected apiClient call to throw");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(403);
      expect(apiErr.code).toBe("PERMISSION_DENIED");
      expect(apiErr.message).toBe("User lacks view permission");
    }
  });
});
