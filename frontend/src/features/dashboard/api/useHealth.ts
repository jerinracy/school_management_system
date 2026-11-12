import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface HealthResponse {
  status: string;
  database: string;
  redis: string;
  version: string;
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.status === "string" &&
    typeof record.database === "string" &&
    typeof record.redis === "string" &&
    typeof record.version === "string"
  );
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data, error, response } = await apiClient.GET("/api/v1/health/");
  if (error || !response.ok) {
    throw new Error(`Health endpoint failed with status ${response.status}`);
  }
  if (!isHealthResponse(data)) {
    throw new Error("Unexpected response shape from /api/v1/health/");
  }
  return data;
}

export function useHealth() {
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: fetchHealth,
    staleTime: 15_000,
  });
}
