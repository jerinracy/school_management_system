import { http, HttpResponse } from "msw";

export const handlers = [
  http.get(/\/api\/v1\/institutions\/public-branding\/$/, () => {
    return HttpResponse.json({
      id: "inst-test-1",
      name_en: "Dhaka Model Academy",
      name_bn: "ঢাকা মডেল একাডেমি",
      eiin: "106601",
      board: "dhaka",
      type: "secondary",
      logo: null,
      logo_url: null,
      phone: "+8801711000000",
      email: "info@dhakamodel.edu.bd",
      website: "https://dhakamodel.edu.bd",
      address_line: "Dhanmondi, Dhaka",
      district: "Dhaka",
      division: "Dhaka",
    });
  }),
  http.get(/\/api\/v1\/health\/$/, () => {
    return HttpResponse.json({
      status: "ok",
      database: "connected",
      redis: "connected",
      version: "1.0.0",
    });
  }),
];
