import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { RoutineBuilderPage } from "@/features/academics/pages/RoutineBuilderPage";

function renderRoutinePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  useAuthStore.getState().setTokens("acc", "ref");
  useAuthStore.getState().setUser({
    id: "user-admin",
    username: "vice_principal",
    full_name: "Vice Principal",
    phone: "+8801700000001",
    email: "vp@example.com",
    user_type: "super_admin",
    institution_id: "inst-1",
    roles: ["SuperAdmin"],
    permissions: ["academics.manage", "academics.view"],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RoutineBuilderPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RoutineBuilderPage & Conflict Pre-Check", () => {
  const mockClasses = [
    {
      id: "class-10",
      name: "Class 10",
      code: "C10",
      order: 10,
      medium_display: "Bangla Medium",
      sections_count: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  const mockPeriods = [
    {
      id: "period-1",
      shift: "shift-morning",
      shift_name: "Morning",
      name: "1st Period",
      start_time: "08:00:00",
      end_time: "08:45:00",
      order: 1,
      is_break: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  const mockSubjects = [
    {
      id: "sub-phy",
      code: "174",
      name_en: "Physics",
      name_bn: "পদার্থবিজ্ঞান",
      type_display: "Compulsory",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  const mockRooms = [
    {
      id: "room-201",
      branch_name: "Main Campus",
      name: "Science Lab 201",
      capacity: 40,
      type_display: "Lab",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  const mockSections = [
    {
      id: "sec-10a",
      class_level: "class-10",
      class_level_name: "Class 10",
      shift: "shift-morning",
      shift_name: "Morning",
      session: "sess-2026",
      session_name: "2026 Academic Year",
      name: "Section A (Padma)",
      capacity: 50,
      teacher_name: "Dr. Rahman",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  const mockRoutine = [
    {
      id: "slot-1",
      section: "sec-10a",
      section_name: "Section A (Padma)",
      class_level_name: "Class 10",
      weekday: 0,
      weekday_display: "Sunday",
      period: "period-1",
      period_name: "1st Period",
      start_time: "08:00:00",
      end_time: "08:45:00",
      subject: "sub-phy",
      subject_name_en: "Physics",
      subject_name_bn: "পদার্থবিজ্ঞান",
      teacher_name: "Dr. Rahman",
      room_name: "Science Lab 201",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  beforeEach(async () => {
    await i18n.changeLanguage("en");
    server.use(
      http.get(/\/api\/v1\/academics\/classes\//, () => {
        return HttpResponse.json({ results: mockClasses });
      }),
      http.get(/\/api\/v1\/academics\/periods\//, () => {
        return HttpResponse.json({ results: mockPeriods });
      }),
      http.get(/\/api\/v1\/academics\/subjects\//, () => {
        return HttpResponse.json({ results: mockSubjects });
      }),
      http.get(/\/api\/v1\/academics\/rooms\//, () => {
        return HttpResponse.json({ results: mockRooms });
      }),
      http.get(/\/api\/v1\/academics\/sections\//, () => {
        return HttpResponse.json({ results: mockSections });
      }),
      http.get(/\/api\/v1\/academics\/routine\//, () => {
        return HttpResponse.json({ results: mockRoutine });
      }),
      http.get(/\/api\/v1\/staff\/staff\//, () => {
        return HttpResponse.json({ results: [{ id: "staff-1", full_name: "Dr. Rahman" }] });
      }),
      http.post(/\/api\/v1\/academics\/routine\/validate\//, () => {
        return HttpResponse.json({
          is_valid: false,
          errors: ["Teacher double-booking detected for Dr. Rahman at 08:00 on Sunday."],
          warnings: ["Science Lab 201 capacity (40) is smaller than section size (50)."],
        });
      }),
    );
  });

  it("renders routine timetable grid and slots", async () => {
    renderRoutinePage();

    await waitFor(
      () => {
        expect(screen.getByText("Weekly Routine & Timetable Builder")).toBeInTheDocument();
        expect(screen.getByText("Physics")).toBeInTheDocument();
      },
      { timeout: 8000 }
    );

    expect(screen.getByText("Sunday")).toBeInTheDocument();
    expect(screen.getAllByText("Dr. Rahman").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Science Lab 201")).toBeInTheDocument();
    expect(screen.getByText(/Class Teacher \(Section Supervisor\)/i)).toBeInTheDocument();
  });

  it("renders Class Teacher supervisor banner and allows opening assignment modal", async () => {
    renderRoutinePage();

    await waitFor(() => {
      expect(screen.getByText(/Class Teacher \(Section Supervisor\)/i)).toBeInTheDocument();
    });

    const assignTeacherBtn = screen.getByRole("button", { name: /Class Teacher/i });
    expect(assignTeacherBtn).toBeInTheDocument();
    await userEvent.click(assignTeacherBtn);

    await waitFor(() => {
      expect(screen.getByText(/Assign Section Class Teacher/i)).toBeInTheDocument();
      expect(
        screen.getByText(/A teacher can only be assigned as Class Teacher to ONE section per session/i)
      ).toBeInTheDocument();
    });
  });

  it("triggers conflict validation pre-check and renders warnings and errors", async () => {
    renderRoutinePage();

    await waitFor(() => {
      expect(screen.getByText("Assign Period Slot")).toBeInTheDocument();
    });

    const assignBtn = screen.getByText("Assign Period Slot");
    await userEvent.click(assignBtn);

    const validateBtn = screen.getByText("Validate Conflict Pre-Check");
    await userEvent.click(validateBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Teacher double-booking detected for Dr. Rahman/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Science Lab 201 capacity \(40\) is smaller than section size \(50\)/i),
      ).toBeInTheDocument();
    });
  });
});
