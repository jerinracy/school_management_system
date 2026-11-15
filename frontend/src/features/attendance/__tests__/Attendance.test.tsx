import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import DailyAttendancePage from "@/features/attendance/pages/DailyAttendancePage";
import AttendanceCorrectionsPage from "@/features/attendance/pages/AttendanceCorrectionsPage";

const mockAttendance = [
  {
    id: "att-1",
    date: "2026-11-14",
    user_type: "student",
    student: "stu-1",
    student_name: "Tanvir Hasan",
    student_roll: "Roll 01",
    status: "present",
    first_in: "2026-11-14T07:55:00Z",
    last_out: "2026-11-14T13:45:00Z",
    total_minutes: 350,
    minutes_late: 0,
  },
  {
    id: "att-2",
    date: "2026-11-14",
    user_type: "student",
    student: "stu-2",
    student_name: "Nusrat Jahan",
    student_roll: "Roll 02",
    status: "late",
    first_in: "2026-11-14T08:22:00Z",
    last_out: "2026-11-14T13:50:00Z",
    total_minutes: 328,
    minutes_late: 22,
  },
  {
    id: "att-3",
    date: "2026-11-14",
    user_type: "student",
    student: "stu-3",
    student_name: "Farhan Ahmed",
    student_roll: "Roll 03",
    status: "absent",
    first_in: null,
    last_out: null,
    total_minutes: 0,
    minutes_late: 0,
  },
];

const mockCorrections = [
  {
    id: "corr-1",
    target_date: "2026-11-13",
    student_name: "Tanvir Hasan",
    staff_name: null,
    requested_by_name: "Parent (Guardian)",
    reason: "Student arrived at 8:02 AM but biometric machine scanner was frozen.",
    status_before: "absent",
    status_after: "present",
    time_in_after: "08:02:00",
    time_out_after: "13:45:00",
    approval_status: "pending",
  },
];

function setupAuth() {
  useAuthStore.getState().setTokens("acc", "ref");
  useAuthStore.getState().setUser({
    id: "user-admin",
    username: "principal",
    full_name: "School Principal",
    phone: "+8801700000000",
    email: "principal@example.com",
    user_type: "super_admin",
    institution_id: "inst-1",
    roles: ["SuperAdmin"],
    permissions: ["attendance.view", "attendance.manage"],
  });
}

describe("DailyAttendancePage", () => {
  beforeEach(() => {
    setupAuth();
    server.use(
      http.get("/api/v1/attendance/daily/", () => {
        return HttpResponse.json({
          count: mockAttendance.length,
          next: null,
          previous: null,
          results: mockAttendance,
        });
      }),
      http.get("/api/v1/academics/classes/", () => {
        return HttpResponse.json({ count: 0, results: [] });
      }),
    );
  });

  it("renders daily attendance records, roster and statistics", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DailyAttendancePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Tanvir Hasan")).toBeInTheDocument();
      expect(screen.getByText("Nusrat Jahan")).toBeInTheDocument();
      expect(screen.getByText("Farhan Ahmed")).toBeInTheDocument();
    });

    expect(screen.getByText("Roll 01")).toBeInTheDocument();
    expect(screen.getByText("Roll 02")).toBeInTheDocument();
  });
});

describe("AttendanceCorrectionsPage", () => {
  beforeEach(() => {
    setupAuth();
    server.use(
      http.get("/api/v1/attendance/corrections/", () => {
        return HttpResponse.json({
          count: mockCorrections.length,
          next: null,
          previous: null,
          results: mockCorrections,
        });
      }),
    );
  });

  it("renders pending attendance correction requests queue", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AttendanceCorrectionsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Tanvir Hasan (Student)")).toBeInTheDocument();
      expect(screen.getByText("2026-11-13")).toBeInTheDocument();
      expect(screen.getByText(/biometric machine scanner was frozen/)).toBeInTheDocument();
    });

    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
  });
});
