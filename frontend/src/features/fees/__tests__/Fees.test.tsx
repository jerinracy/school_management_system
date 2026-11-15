import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import InvoicesListPage from "@/features/fees/pages/InvoicesListPage";
import { MoneyReceiptPreview, type ReceiptData } from "@/features/fees/components/MoneyReceiptPreview";

const mockInvoices = [
  {
    id: "inv-1",
    invoice_number: "INV-202611-0001",
    student: "stu-1",
    student_code: "STU-2026-001",
    student_name: "Rafiq Ahmed",
    session: "sess-1",
    session_name: "Academic Year 2026",
    invoice_type: "monthly",
    title: "Monthly Tuition November 2026",
    billing_month: 11,
    billing_year: 2026,
    subtotal_amount: "1500.00",
    waiver_amount: "0.00",
    fine_amount: "0.00",
    total_payable: "1500.00",
    paid_amount: "1500.00",
    due_amount: "0.00",
    status: "paid",
    issue_date: "2026-11-01",
    due_date: "2026-11-10",
    created_at: "2026-11-01T10:00:00Z",
  },
  {
    id: "inv-2",
    invoice_number: "INV-202611-0002",
    student: "stu-2",
    student_code: "STU-2026-002",
    student_name: "Sumaiya Akter",
    session: "sess-1",
    session_name: "Academic Year 2026",
    invoice_type: "monthly",
    title: "Monthly Tuition November 2026",
    billing_month: 11,
    billing_year: 2026,
    subtotal_amount: "1500.00",
    waiver_amount: "300.00",
    fine_amount: "50.00",
    total_payable: "1250.00",
    paid_amount: "0.00",
    due_amount: "1250.00",
    status: "overdue",
    issue_date: "2026-11-01",
    due_date: "2026-11-10",
    created_at: "2026-11-01T10:00:00Z",
  },
];

const mockReceiptData: ReceiptData = {
  receipt_number: "REC-2026-00129",
  payment_date: "2026-11-15",
  payment_method: "BKASH",
  transaction_id: "BKS88291039",
  student_name: "Tanvir Hasan",
  student_code: "STU-2026-003",
  class_name: "Class 10",
  section_name: "A",
  roll_no: 5,
  items: [
    { head_name: "Monthly Tuition Fee", amount: "1200.00" },
    { head_name: "Computer Lab Fee", amount: "300.00" },
  ],
  subtotal: "1500.00",
  total_paid: "1500.00",
};

function setupAuth() {
  useAuthStore.getState().setTokens("acc", "ref");
  useAuthStore.getState().setUser({
    id: "user-admin",
    username: "accountant",
    full_name: "School Accountant",
    phone: "+8801700000000",
    email: "accountant@example.com",
    user_type: "admin",
    institution_id: "inst-1",
    roles: ["Accountant"],
    permissions: ["fees.view", "fees.change", "accounting.view"],
  });
}

describe("Fees & Billing Module Tests", () => {
  beforeEach(() => {
    setupAuth();
    server.use(
      http.get("*/api/v1/fees/invoices/", () => {
        return HttpResponse.json({ results: mockInvoices, count: 2 });
      }),
      http.get("*/api/v1/academics/classes/", () => {
        return HttpResponse.json({ results: [{ id: "c-1", name: "Class 10" }], count: 1 });
      }),
      http.get("*/api/v1/institutions/sessions/", () => {
        return HttpResponse.json({ results: [{ id: "sess-1", name: "Academic Year 2026" }], count: 1 });
      }),
    );
  });

  it("renders invoices directory with KPIs and invoice table rows", async () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <InvoicesListPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("INV-202611-0001")).toBeInTheDocument();
      expect(screen.getByText("INV-202611-0002")).toBeInTheDocument();
      expect(screen.getByText("Rafiq Ahmed")).toBeInTheDocument();
      expect(screen.getByText("Sumaiya Akter")).toBeInTheDocument();
    });
  });

  it("renders 3-part Money Receipt preview with Student, Office, and Bank copies", () => {
    render(
      <MemoryRouter>
        <MoneyReceiptPreview receipt={mockReceiptData} onClose={() => {}} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Student Copy")).toBeInTheDocument();
    expect(screen.getByText("Office Copy")).toBeInTheDocument();
    expect(screen.getByText("Bank Copy")).toBeInTheDocument();
    expect(screen.getAllByText("Tanvir Hasan").length).toBe(3);
    expect(screen.getAllByText("REC-2026-00129").length).toBeGreaterThanOrEqual(3);
    expect(screen.getAllByText("৳1500.00").length).toBeGreaterThanOrEqual(3);
  });
});
