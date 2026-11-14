import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { AppRoutes } from "@/App";
import i18n from "@/i18n";
import { ThemeProvider } from "@/lib/theme";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";

function renderAuth(initialEntry = "/login") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  useAuthStore.getState().logout();
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

describe("LoginPage & Auth Flows", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage("en");
  });

  it("renders login form and switches language offline", async () => {
    renderAuth();

    expect(screen.getByText("Admin Sign In")).toBeInTheDocument();
    expect(screen.getByLabelText(/Phone or Username/i)).toBeInTheDocument();

    const banglaBtn = screen.getByRole("button", { name: /switch language to bangla/i });
    await userEvent.click(banglaBtn);

    expect(screen.getByText("অ্যাডমিন সাইন ইন")).toBeInTheDocument();
  });

  it("submits password login successfully and stores tokens", async () => {
    server.use(
      http.post(/\/api\/v1\/auth\/login\/$/, () => {
        return HttpResponse.json({
          access: "jwt-access-123",
          refresh: "jwt-refresh-123",
          user: {
            id: "u-1",
            username: "teacher_01",
            full_name: "Fatima Begum",
            phone: "+8801711111111",
            email: "fatima@example.com",
            user_type: "teacher",
            institution_id: "inst-1",
            roles: ["Teacher"],
            permissions: ["attendance.view"],
            must_change_password: false,
          },
        });
      }),
    );

    renderAuth();

    await userEvent.type(screen.getByPlaceholderText("+8801XXXXXXXXX"), "+8801711111111");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "Secret123!");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user?.username).toBe("teacher_01");
    });
  });

  it("displays locked message on HTTP 429 ACCOUNT_LOCKED", async () => {
    server.use(
      http.post(/\/api\/v1\/auth\/login\/$/, () => {
        return HttpResponse.json(
          {
            code: "ACCOUNT_LOCKED",
            message: "Account locked due to multiple failed attempts. Try again in 15 minutes.",
          },
          { status: 429 },
        );
      }),
    );

    renderAuth();

    await userEvent.type(screen.getByPlaceholderText("+8801XXXXXXXXX"), "+8801711111111");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "Wrong123!");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText(/Account locked due to multiple failed attempts/i)).toBeInTheDocument();
    });
  });

  it("supports phone OTP login request and code verification", async () => {
    let sentPhone = "";
    let verifiedCode = "";

    server.use(
      http.post(/\/api\/v1\/auth\/otp\/request\/$/, async ({ request }) => {
        const body = (await request.json()) as { phone: string };
        sentPhone = body.phone;
        return HttpResponse.json({ message: "OTP sent", expires_in: 300 });
      }),
      http.post(/\/api\/v1\/auth\/otp\/verify\/$/, async ({ request }) => {
        const body = (await request.json()) as { phone: string; code: string };
        verifiedCode = body.code;
        return HttpResponse.json({
          access: "otp-jwt-access",
          refresh: "otp-jwt-refresh",
          user: {
            id: "u-2",
            username: "guardian_01",
            full_name: "Abdul Karim",
            phone: "+8801811111111",
            email: "karim@example.com",
            user_type: "guardian",
            institution_id: "inst-1",
            roles: ["Guardian"],
            permissions: [],
            must_change_password: false,
          },
        });
      }),
    );

    renderAuth();

    // Switch to OTP tab
    await userEvent.click(screen.getByRole("tab", { name: /phone otp/i }));

    const phoneInput = screen.getByLabelText(/Mobile Number/i);
    await userEvent.type(phoneInput, "+8801811111111");
    await userEvent.click(screen.getByRole("button", { name: /Send OTP Code/i }));

    await waitFor(() => {
      expect(screen.getByText(/Enter 6-digit Code/i)).toBeInTheDocument();
    });
    expect(sentPhone).toBe("+8801811111111");

    const codeInput = screen.getByLabelText(/Enter 6-digit Code/i);
    await userEvent.type(codeInput, "123456");
    await userEvent.click(screen.getByRole("button", { name: /Verify & Sign In/i }));

    await waitFor(() => {
      expect(verifiedCode).toBe("123456");
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user?.full_name).toBe("Abdul Karim");
    });
  });
});
