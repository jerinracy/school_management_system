import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { Can, ProtectedRoute } from "@/features/auth/permissions";
import { useAuthStore } from "@/features/auth/store/authStore";

describe("Permissions & ProtectedRoute", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    useAuthStore.getState().setIsRestoring(false);
  });

  it("redirects unauthenticated user to /login", () => {
    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Secret Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Secret Content")).not.toBeInTheDocument();
  });

  it("redirects to /403 when user lacks required permission", () => {
    useAuthStore.getState().setTokens("acc", "ref");
    useAuthStore.getState().setUser({
      id: "u-1",
      username: "teacher",
      full_name: "Teacher",
      phone: "+8801700000000",
      email: "t@example.com",
      user_type: "teacher",
      institution_id: "inst-1",
      roles: ["Teacher"],
      permissions: ["attendance.view"],
    });

    render(
      <MemoryRouter initialEntries={["/finance"]}>
        <Routes>
          <Route path="/403" element={<div>Access Denied (403)</div>} />
          <Route
            path="/finance"
            element={
              <ProtectedRoute perm="fees.manage">
                <div>Finance Workspace</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Access Denied (403)")).toBeInTheDocument();
    expect(screen.queryByText("Finance Workspace")).not.toBeInTheDocument();
  });

  it("allows access when user has permission", () => {
    useAuthStore.getState().setTokens("acc", "ref");
    useAuthStore.getState().setUser({
      id: "u-1",
      username: "accountant",
      full_name: "Accountant",
      phone: "+8801700000000",
      email: "acc@example.com",
      user_type: "accountant",
      institution_id: "inst-1",
      roles: ["Accountant"],
      permissions: ["fees.manage"],
    });

    render(
      <MemoryRouter initialEntries={["/finance"]}>
        <Routes>
          <Route
            path="/finance"
            element={
              <ProtectedRoute perm="fees.manage">
                <div>Finance Workspace</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Finance Workspace")).toBeInTheDocument();
  });

  it("superadmin/admin bypasses permission checks", () => {
    useAuthStore.getState().setTokens("acc", "ref");
    useAuthStore.getState().setUser({
      id: "u-admin",
      username: "superadmin",
      full_name: "Super Administrator",
      phone: "+8801700000000",
      email: "admin@example.com",
      user_type: "admin",
      institution_id: "inst-1",
      roles: ["Admin"],
      permissions: [], // empty permissions, but admin
    });

    render(
      <MemoryRouter initialEntries={["/any-secret"]}>
        <Routes>
          <Route
            path="/any-secret"
            element={
              <ProtectedRoute perm="super.secret.perm">
                <div>Super Secret Workspace</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Super Secret Workspace")).toBeInTheDocument();
  });

  it("<Can> component renders children only when authorized", () => {
    useAuthStore.getState().setUser({
      id: "u-1",
      username: "teacher",
      full_name: "Teacher",
      phone: "+8801700000000",
      email: "t@example.com",
      user_type: "teacher",
      institution_id: "inst-1",
      roles: ["Teacher"],
      permissions: ["grades.edit"],
    });

    render(
      <div>
        <Can perm="grades.edit">
          <button>Submit Marks</button>
        </Can>
        <Can perm="fees.refund" fallback={<span>No Refund Permission</span>}>
          <button>Issue Refund</button>
        </Can>
      </div>,
    );

    expect(screen.getByRole("button", { name: "Submit Marks" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Issue Refund" })).not.toBeInTheDocument();
    expect(screen.getByText("No Refund Permission")).toBeInTheDocument();
  });
});
