import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { SessionsTermsPage } from "@/features/institutions/pages/SessionsTermsPage";

function renderSessionsPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

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
    permissions: ["institutions.manage", "institutions.view"],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SessionsTermsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SessionsTermsPage", () => {
  const mockSessions = [
    {
      id: "sess-2026",
      name: "2026 Academic Year",
      is_current: true,
      start_date: "2026-01-01",
      end_date: "2026-12-31",
      institution: "inst-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "sess-2025",
      name: "2025 Academic Year",
      is_current: false,
      start_date: "2025-01-01",
      end_date: "2025-12-31",
      institution: "inst-1",
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    },
  ];

  const mockTerms = [
    {
      id: "term-1",
      session: "sess-2026",
      name: "First Term",
      start_date: "2026-01-01",
      end_date: "2026-04-30",
      institution: "inst-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];

  beforeEach(async () => {
    await i18n.changeLanguage("en");
    server.use(
      http.get(/\/api\/v1\/institutions\/sessions\//, () => {
        return HttpResponse.json({ results: mockSessions });
      }),
      http.get(/\/api\/v1\/institutions\/terms\//, () => {
        return HttpResponse.json({ results: mockTerms });
      }),
      http.post(/\/api\/v1\/institutions\/sessions\/(.+)\/activate\//, () => {
        return HttpResponse.json({ success: true, is_current: true });
      }),
      http.post(/\/api\/v1\/institutions\/sessions\/(.+)\/close\//, () => {
        return HttpResponse.json({ success: true, is_current: false });
      }),
    );
  });

  it("renders academic sessions and active terms", async () => {
    renderSessionsPage();

    await waitFor(() => {
      expect(screen.getAllByText("2026 Academic Year").length).toBeGreaterThan(0);
      expect(screen.getByText("2025 Academic Year")).toBeInTheDocument();
      expect(screen.getByText("Active")).toBeInTheDocument();
      expect(screen.getByText("First Term")).toBeInTheDocument();
    });
  });

  it("opens confirmation dialog when activating a non-current session", async () => {
    renderSessionsPage();

    await waitFor(() => {
      expect(screen.getByText("2025 Academic Year")).toBeInTheDocument();
    });

    const activateBtn = screen.getByRole("button", { name: "Activate" });
    await userEvent.click(activateBtn);

    await waitFor(() => {
      expect(screen.getByText("Activate Academic Session?")).toBeInTheDocument();
      expect(
        screen.getByText(/Any previously active session will be marked inactive/i),
      ).toBeInTheDocument();
    });
  });

  it("opens confirmation dialog when closing current session", async () => {
    renderSessionsPage();

    await waitFor(() => {
      expect(screen.getByText("Close Session")).toBeInTheDocument();
    });

    const closeBtn = screen.getByText("Close Session");
    await userEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.getByText("Close Academic Session?")).toBeInTheDocument();
    });
  });
});
