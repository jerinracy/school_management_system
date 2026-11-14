import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { CopySessionWizardPage } from "@/features/academics/pages/CopySessionWizardPage";

function renderWizardPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  useAuthStore.getState().setTokens("acc", "ref");
  useAuthStore.getState().setUser({
    id: "user-admin",
    username: "admin_user",
    full_name: "System Admin",
    phone: "+8801700000002",
    email: "admin@example.com",
    user_type: "super_admin",
    institution_id: "inst-1",
    roles: ["SuperAdmin"],
    permissions: ["academics.manage"],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CopySessionWizardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CopySessionWizardPage", () => {
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

  beforeEach(async () => {
    await i18n.changeLanguage("en");
    server.use(
      http.get(/\/api\/v1\/institutions\/sessions\//, () => {
        return HttpResponse.json({ results: mockSessions });
      }),
      http.post(/\/api\/v1\/academics\/copy-session\//, async ({ request }) => {
        const body = (await request.json()) as { dry_run?: boolean };
        return HttpResponse.json({
          success: true,
          dry_run: !!body.dry_run,
          source_session: "sess-2025",
          target_session: "sess-2026",
          sections_created: 14,
          sections_skipped: 2,
          class_subjects_created: 82,
          class_subjects_skipped: 0,
        });
      }),
    );
  });

  it("renders wizard steps and runs dry-run simulation preview", async () => {
    renderWizardPage();

    await waitFor(() => {
      expect(
        screen.getByText("Step 1: Select Source and Destination Sessions"),
      ).toBeInTheDocument();
    });

    const simulateBtn = screen.getByText("Simulate Rollover (Dry-Run)");
    await userEvent.click(simulateBtn);

    await waitFor(() => {
      expect(screen.getByText("Step 2: Dry-Run Simulation Preview")).toBeInTheDocument();
      expect(screen.getByText("+14")).toBeInTheDocument();
      expect(screen.getByText("+82")).toBeInTheDocument();
    });

    const executeBtn = screen.getByText("Confirm & Execute Rollover");
    await userEvent.click(executeBtn);

    await waitFor(() => {
      expect(screen.getByText("Step 3: Rollover Completed")).toBeInTheDocument();
      expect(
        screen.getByText(/Academic Structure Successfully Copied/i),
      ).toBeInTheDocument();
    });
  });
});
