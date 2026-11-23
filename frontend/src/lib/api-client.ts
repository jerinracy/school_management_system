import createClient from "openapi-fetch";
import i18n from "@/i18n";
import { parseApiError, ApiError } from "@/lib/errors";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useAcademicContextStore } from "@/features/institutions/store/academicContextStore";
import type { paths } from "@/types/api";

const baseUrl =
  typeof window !== "undefined" && window.location.origin.startsWith("http")
    ? window.location.origin
    : "http://localhost";

export const apiClient = createClient<paths>({
  baseUrl,
  fetch: (request) => globalThis.fetch(request),
  headers: {
    Accept: "application/json",
  },
});

let refreshPromise: Promise<string | null> | null = null;
const requestClones = new Map<string, Request>();

async function executeTokenRefresh(currentRefreshToken: string): Promise<string | null> {
  try {
    const response = await fetch(`${baseUrl}/api/v1/auth/refresh/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ refresh: currentRefreshToken }),
    });

    if (!response.ok) {
      useAuthStore.getState().logout();
      return null;
    }

    const data = (await response.json()) as { access: string; refresh: string };
    useAuthStore.getState().setTokens(data.access, data.refresh);
    return data.access;
  } catch {
    useAuthStore.getState().logout();
    return null;
  } finally {
    refreshPromise = null;
  }
}

export async function requestTokenRefresh(): Promise<string | null> {
  const currentRefresh = useAuthStore.getState().refreshToken;
  if (!currentRefresh) {
    useAuthStore.getState().logout();
    return null;
  }

  if (!refreshPromise) {
    refreshPromise = executeTokenRefresh(currentRefresh);
  }
  return refreshPromise;
}

apiClient.use({
  onRequest({ request }) {
    request.headers.set("Accept-Language", i18n.language === "bn" ? "bn" : "en");

    // Generate request id for correlation
    let requestId = request.headers.get("X-Request-ID");
    if (!requestId) {
      requestId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
      request.headers.set("X-Request-ID", requestId);
    }

    const token = useAuthStore.getState().accessToken;
    if (token && !request.headers.has("Authorization")) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }

    const sessionId = useAcademicContextStore.getState().selectedSessionId;
    if (sessionId && !request.headers.has("X-Academic-Session")) {
      request.headers.set("X-Academic-Session", sessionId);
    }

    // Save an unconsumed clone before fetch consumes the request body
    try {
      requestClones.set(requestId, request.clone());
    } catch {
      // Ignore if cloning is unsupported
    }

    return request;
  },

  async onResponse({ request, response }) {
    const requestId = request.headers.get("X-Request-ID");
    const clone = requestId ? requestClones.get(requestId) : null;

    try {
      // If unauthorized and we have a refresh token, attempt single-flight refresh
      if (response.status === 401 && !request.url.includes("/api/v1/auth/refresh/") && !request.url.includes("/api/v1/auth/login/")) {
        const newAccess = await requestTokenRefresh();
        if (newAccess) {
          const targetRequest = clone || request;
          try {
            const retryHeaders = new Headers(targetRequest.headers);
            retryHeaders.set("Authorization", `Bearer ${newAccess}`);
            const retryRequest = new Request(targetRequest, { headers: retryHeaders });
            const retryResponse = await fetch(retryRequest);
            if (!retryResponse.ok) {
              let errorBody: unknown = null;
              try {
                const cloned = retryResponse.clone();
                errorBody = await cloned.json();
              } catch {
                // Non-JSON error body
              }
              throw parseApiError(retryResponse.status, errorBody);
            }
            return retryResponse;
          } catch (retryErr) {
            if (retryErr instanceof ApiError) throw retryErr;
          }
        }
      }

      if (!response.ok) {
        let body: unknown = null;
        try {
          const cloned = response.clone();
          body = await cloned.json();
        } catch {
          // Non-JSON error body
        }
        throw parseApiError(response.status, body);
      }

      return response;
    } finally {
      if (requestId) {
        requestClones.delete(requestId);
      }
    }
  },
});
