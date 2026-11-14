import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { AppRoutes } from "@/App";
import i18n, { LANGUAGE_STORAGE_KEY } from "@/i18n";
import { ThemeProvider } from "@/lib/theme";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";

function renderDashboard(initialEntry = "/", isAuthenticated = true) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  if (isAuthenticated) {
    useAuthStore.getState().setTokens("mock-access", "mock-refresh");
    useAuthStore.getState().setUser({
      id: "test-admin-id",
      username: "admin",
      full_name: "Admin User",
      phone: "+8801700000000",
      email: "admin@example.com",
      user_type: "admin",
      institution_id: "inst-1",
      roles: ["Admin"],
      permissions: ["students.view", "attendance.view", "exams.view", "fees.view", "staff.view", "devices.view", "system.view"],
    });
  } else {
    useAuthStore.getState().logout();
  }
  useAuthStore.getState().setIsRestoring(false);

  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("DashboardHomePage", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage("en");
  });

  it("shows login page when unauthenticated", () => {
    renderDashboard("/", false);
    expect(screen.getByText("Admin Sign In")).toBeInTheDocument();
  });

  it("renders live backend health KPIs from /api/v1/health/", async () => {
    renderDashboard();

    expect(screen.getByText("Institution Overview")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Operational")).toBeInTheDocument();
      expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    });
  });

  it("shows an error alert when /api/v1/health/ fails", async () => {
    server.use(
      http.get(/\/api\/v1\/health\/$/, () => {
        return HttpResponse.json({ status: "error" }, { status: 503 });
      }),
    );

    renderDashboard();

    await waitFor(
      () => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText("Unable to reach backend API")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("switches between English and Bangla offline without reloading", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    });

    const bnButton = screen.getByRole("button", { name: "Switch language to Bangla" });
    await user.click(bnButton);

    expect(screen.getByText("প্রতিষ্ঠান সারসংক্ষেপ")).toBeInTheDocument();
    expect(screen.getByText("v১.০.০")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("bn");
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("bn");

    const enButton = screen.getByRole("button", { name: "ভাষা ইংরেজিতে পরিবর্তন করুন" });
    await user.click(enButton);

    expect(screen.getByText("Institution Overview")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });
});
