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
  http.get(/\/api\/v1\/reports\/dashboard\/kpis\/$/, () => {
    return HttpResponse.json({
      date: "2026-11-22",
      role_variant: "executive",
      headcount: {
        total_teachers: 24,
        total_office_staff: 8,
        total_students: 650,
        morning_shift_students: 320,
        day_shift_students: 330,
        total_classes: 10,
        total_sections: 22,
      },
      attendance: {
        student: { present: 580, late: 20, absent: 40, leave: 10 },
        staff: { present: 30, late: 1, absent: 1, leave: 0 },
      },
      attendance_rates: {
        student_present_pct: 92.3,
        staff_present_pct: 96.9,
      },
      devices: {
        online: 2,
        offline: 0,
      },
      upcoming_exams_count: 2,
      pending_approvals: {
        attendance_corrections: 1,
      },
    });
  }),
];
