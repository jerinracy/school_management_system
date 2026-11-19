export interface ApiErrorPayload {
  code?: string;
  message?: string;
  details?: Record<string, unknown> | Array<unknown> | string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown> | Array<unknown> | string | null;

  constructor(status: number, payload?: ApiErrorPayload) {
    const code = payload?.code ?? (status === 401 ? "AUTHENTICATION_REQUIRED" : "API_ERROR");
    const message = payload?.message || `Request failed with status ${status}`;
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = payload?.details ?? null;
  }

  isFieldErrors(): this is ApiError & { details: Record<string, string[] | string> } {
    return (
      this.details !== null &&
      typeof this.details === "object" &&
      !Array.isArray(this.details)
    );
  }
}

export function parseApiError(status: number, data: unknown): ApiError {
  if (typeof data === "object" && data !== null) {
    const record = data as Record<string, unknown>;
    const code = typeof record.code === "string" ? record.code : undefined;
    const message =
      typeof record.message === "string"
        ? record.message
        : typeof record.detail === "string"
          ? record.detail
          : undefined;
    const details = (record.details ?? (record.detail && !message ? record.detail : null)) as
      | Record<string, unknown>
      | Array<unknown>
      | string
      | null;

    return new ApiError(status, { code, message, details: details ?? record });
  }

  return new ApiError(status, {
    message: typeof data === "string" ? data : undefined,
  });
}
