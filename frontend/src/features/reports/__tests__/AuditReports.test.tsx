import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";

import { AuditLogsPage } from "../pages/AuditLogsPage";
import { ActivityLogsPage } from "../pages/ActivityLogsPage";
import { ReportDefinitionsPage } from "../pages/ReportDefinitionsPage";
import { ReportExportsPage } from "../pages/ReportExportsPage";
import { BulkImportsPage } from "../pages/BulkImportsPage";

const mockAuditLogs = [
  {
    id: "aud-1",
    actor: "usr-admin-1",
    actor_username: "auditadmin",
    action: "update",
    module: "fees",
    target_model: "StudentInvoice",
    target_object_id: "inv-9921",
    target_repr: "Invoice #INV-2026-0042 (Rahim Chowdhury)",
    before_data: { status: "issued", due_amount: "3500.00" },
    after_data: { status: "paid", due_amount: "0.00" },
    changed_fields: ["status", "due_amount"],
    ip_address: "103.114.98.22",
    user_agent: "Mozilla/5.0 Chrome/130.0",
    request_id: "req-sec-9901",
    metadata: { source: "pos_terminal" },
    created_at: "2026-11-15T10:30:00Z",
  },
];

const mockActivityLogs = [
  {
    id: "act-1",
    actor: "usr-admin-1",
    actor_username: "auditadmin",
    activity_type: "export",
    module: "reports",
    description: "Exported student roster report to XLSX format",
    ip_address: "103.114.98.22",
    user_agent: "Mozilla/5.0 Chrome/130.0",
    metadata: { dataset: "students", row_count: 450 },
    created_at: "2026-11-15T11:00:00Z",
  },
];

const mockDefinitions = [
  {
    id: "def-1",
    name: "Class 10 Monthly Fee Collections",
    dataset: "fee_invoices",
    selected_columns: ["invoice_number", "total_payable", "paid_amount", "status"],
    filters: { status: "paid" },
    default_format: "csv",
    is_shared: true,
    created_at: "2026-11-10T08:00:00Z",
    updated_at: "2026-11-15T08:00:00Z",
  },
];

const mockExports = [
  {
    id: "exp-1",
    dataset: "students",
    selected_columns: ["student_id", "name_en", "gender", "status"],
    filters: {},
    export_format: "xlsx",
    status: "completed",
    row_count: 520,
    expires_at: "2026-11-22T00:00:00Z",
    requested_by: "usr-admin-1",
    created_at: "2026-11-15T09:15:00Z",
  },
];

const mockImports = [
  {
    id: "imp-1",
    target_type: "students",
    status: "validated",
    file: "media/reports/imports/students_batch_2026.csv",
    dry_run: true,
    total_rows: 150,
    valid_rows: 148,
    error_rows: 2,
    errors_summary: [
      { row: 14, field: "dob", error: "Invalid date format. Expected YYYY-MM-DD." },
      { row: 82, field: "student_id", error: "Duplicate student_id 'STD-2026-0042' already exists." },
    ],
    uploaded_by: "usr-admin-1",
    created_at: "2026-11-15T12:00:00Z",
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Task F14 - Enterprise Audit Logging & Reporting Dashboard", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: "usr-admin-1",
        username: "auditadmin",
        email: "audit@school.edu.bd",
        phone: "+8801700000000",
        user_type: "admin",
        institution_id: "inst-1",
        roles: ["admin"],
        permissions: ["audit.view", "reports.view", "reports.manage"],
        full_name: "Audit Administrator",
      },
      accessToken: "mock-token",
      refreshToken: "mock-refresh",
      isAuthenticated: true,
    });

    server.use(
      http.get("/api/v1/audit/logs/", () => {
        return HttpResponse.json({ results: mockAuditLogs, count: mockAuditLogs.length });
      }),
      http.get("/api/v1/audit/activities/", () => {
        return HttpResponse.json({ results: mockActivityLogs, count: mockActivityLogs.length });
      }),
      http.get("/api/v1/reports/definitions/", () => {
        return HttpResponse.json({ results: mockDefinitions, count: mockDefinitions.length });
      }),
      http.get("/api/v1/reports/exports/", () => {
        return HttpResponse.json({ results: mockExports, count: mockExports.length });
      }),
      http.get("/api/v1/reports/imports/", () => {
        return HttpResponse.json({ results: mockImports, count: mockImports.length });
      })
    );
  });

  it("renders audit logs table and opens change diff inspector modal", async () => {
    renderWithClient(<AuditLogsPage />);

    expect(await screen.findByText(/auditadmin/i)).toBeInTheDocument();
    expect(screen.getByText(/StudentInvoice/i)).toBeInTheDocument();
    expect(screen.getByText(/103.114.98.22/i)).toBeInTheDocument();

    const inspectBtn = screen.getByRole("button", { name: /Inspect Diff/i });
    expect(inspectBtn).toBeInTheDocument();
    fireEvent.click(inspectBtn);

    expect(await screen.findByText(/Audit Record Diff Inspector/i)).toBeInTheDocument();
    expect(screen.getByText(/State Before Modification:/i)).toBeInTheDocument();
    expect(screen.getByText(/State After Modification:/i)).toBeInTheDocument();
  });

  it("renders user operational activity feed and details modal", async () => {
    renderWithClient(<ActivityLogsPage />);

    expect(await screen.findByText(/auditadmin/i)).toBeInTheDocument();
    expect(screen.getByText(/Exported student roster report to XLSX format/i)).toBeInTheDocument();
    expect(screen.getByText(/\[reports\]/i)).toBeInTheDocument();

    const detailsBtn = screen.getByRole("button", { name: /Details/i });
    expect(detailsBtn).toBeInTheDocument();
    fireEvent.click(detailsBtn);

    expect(await screen.findByText(/Activity Log Record/i)).toBeInTheDocument();
    expect(screen.getByText(/Metadata Payload:/i)).toBeInTheDocument();
  });

  it("renders saved report definitions and opens query builder modal", async () => {
    renderWithClient(<ReportDefinitionsPage />);

    expect(await screen.findByText(/Class 10 Monthly Fee Collections/i)).toBeInTheDocument();
    const feeMatches = screen.getAllByText(/Fee Invoices & Dues/i);
    expect(feeMatches.length).toBeGreaterThan(0);

    const createBtn = screen.getByRole("button", { name: /Create Report Query/i });
    expect(createBtn).toBeInTheDocument();
    fireEvent.click(createBtn);

    expect(await screen.findByText(/Configure Report Definition/i)).toBeInTheDocument();
  });

  it("renders report export jobs and quick export modal", async () => {
    renderWithClient(<ReportExportsPage />);

    expect(await screen.findByText(/520/i)).toBeInTheDocument();
    const completedBadges = screen.getAllByText(/Completed/i);
    expect(completedBadges.length).toBeGreaterThan(0);

    const quickExportBtn = screen.getByRole("button", { name: /Run On-Demand Export/i });
    expect(quickExportBtn).toBeInTheDocument();
    fireEvent.click(quickExportBtn);

    expect(await screen.findByText(/Target Dataset \*/i)).toBeInTheDocument();
  });

  it("renders bulk data importer with validation logs and breakdown modal", async () => {
    renderWithClient(<BulkImportsPage />);

    expect(await screen.findByText("150")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download CSV Template/i })).toBeInTheDocument();
    expect(screen.getByText("148")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();

    const inspectBtn = screen.getByRole("button", { name: /Inspect/i });
    expect(inspectBtn).toBeInTheDocument();
    fireEvent.click(inspectBtn);

    expect(await screen.findByText(/Import Analysis Breakdown/i)).toBeInTheDocument();
    expect(screen.getByText(/Validation Errors \(2\):/i)).toBeInTheDocument();
    expect(screen.getByText(/Duplicate student_id 'STD-2026-0042' already exists/i)).toBeInTheDocument();
  });
});
