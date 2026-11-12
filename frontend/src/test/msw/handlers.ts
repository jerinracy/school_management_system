import { http, HttpResponse } from "msw";

export const handlers = [
  http.get(/\/api\/v1\/health\/$/, () => {
    return HttpResponse.json({
      status: "ok",
      database: "connected",
      redis: "connected",
      version: "1.0.0",
    });
  }),
];
