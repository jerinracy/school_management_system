import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import PayrollRunsListPage from "@/features/payroll/pages/PayrollRunsListPage";
import { PayslipVoucherModal } from "@/features/payroll/components/PayslipVoucherModal";
import type { Payslip } from "@/features/payroll/api/payrollApi";

const mockRuns = [
  {
    id: "run-1",
    month: 7,
    year: 2026,
    title: "Salary Sheet - July 2026",
    status: "approved",
    is_locked: false,
    working_days_in_month: 26,
    absence_deduction_basis: "basic",
    total_gross: "450000.00",
    total_deductions: "35000.00",
    total_net_pay: "415000.00",
    total_employer_pf: "20000.00",
    journal_entry: null,
    journal_entry_voucher_no: "JV-202607-001",
    payslips_count: 15,
    prepared_by: null,
    reviewed_by: null,
    reviewed_at: null,
    approved_by: null,
    approved_at: null,
  },
  {
    id: "run-2",
    month: 6,
    year: 2026,
    title: "Salary Sheet - June 2026",
    status: "paid",
    is_locked: true,
    working_days_in_month: 26,
    absence_deduction_basis: "basic",
    total_gross: "450000.00",
    total_deductions: "32000.00",
    total_net_pay: "418000.00",
    total_employer_pf: "20000.00",
    journal_entry: "je-1",
    journal_entry_voucher_no: "JV-202606-004",
    payslips_count: 15,
    prepared_by: null,
    reviewed_by: null,
    reviewed_at: null,
    approved_by: null,
    approved_at: null,
  },
];

const mockPayslip: Payslip = {
  id: "slip-101",
  payroll_run: "run-1",
  month: 7,
  year: 2026,
  run_status: "approved",
  staff: "staff-1",
  staff_employee_id: "EMP-2026-005",
  staff_name_en: "Mohammad Abdul Karim",
  staff_name_bn: "মোহাম্মদ আব্দুল করিম",
  working_days: 26,
  present_days: "25.0",
  late_days: 1,
  half_days: 0,
  paid_leave_days: "1.0",
  unpaid_leave_days: "0.0",
  absent_days: "0.0",
  overtime_hours: "0.0",
  basic_salary: "35000.00",
  overtime_amount: "0.00",
  bonus_amount: "17500.00",
  gross_earnings: "52500.00",
  absence_deduction_amount: "0.00",
  pf_employee_amount: "3500.00",
  pf_employer_amount: "3500.00",
  loan_deduction_amount: "2000.00",
  total_deductions: "5500.00",
  net_payable: "47000.00",
  payment_method: "bank_transfer",
  is_paid: true,
  paid_at: "2026-07-31T14:30:00Z",
  payment_reference: "BEFTN-202607-0012",
  notes: "Regular July salary with Eid bonus",
  lines: [
    {
      id: "line-1",
      component: "comp-hra",
      name_en: "House Rent Allowance",
      name_bn: "বাড়ি ভাড়া ভাতা",
      line_type: "earning",
      amount: "14000.00",
    },
    {
      id: "line-2",
      component: "comp-med",
      name_en: "Medical Allowance",
      name_bn: "চিকিৎসা ভাতা",
      line_type: "earning",
      amount: "3500.00",
    },
    {
      id: "line-3",
      component: "comp-pf",
      name_en: "Provident Fund (Employee)",
      name_bn: "ভবিষ্যৎ তহবিল কর্তন",
      line_type: "deduction",
      amount: "3500.00",
    },
  ],
  created_at: "2026-07-30T10:00:00Z",
  updated_at: "2026-07-31T14:30:00Z",
};

describe("Task F11: Staff Payroll Management Dashboard", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "mock-token",
      refreshToken: "mock-refresh",
      isAuthenticated: true,
      user: {
        id: "usr-1",
        username: "accountant",
        full_name: "Staff Accountant",
        phone: "+8801712345678",
        email: "accountant@school.edu.bd",
        user_type: "admin",
        roles: ["Accountant"],
        institution_id: "inst-1",
        permissions: ["payroll.view", "payroll.manage", "payroll.approve"],
      },
    });

    server.use(
      http.get("/api/v1/payroll/runs/", () => {
        return HttpResponse.json({
          count: 2,
          next: null,
          previous: null,
          results: mockRuns,
        });
      })
    );
  });

  it("renders payroll runs directory with KPI cards and batch history", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <PayrollRunsListPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Salary Sheet - July 2026")).toBeInTheDocument();
      expect(screen.getByText("Salary Sheet - June 2026")).toBeInTheDocument();
    });

    expect(screen.getByText("JV-202607-001")).toBeInTheDocument();
  });

  it("renders printable bilingual Payslip voucher modal with earnings, deductions and attendance summary", () => {
    render(
      <PayslipVoucherModal
        payslip={mockPayslip}
        isOpen={true}
        onClose={() => {}}
        pdfUrl="/api/v1/payroll/payslips/slip-101/pdf/"
      />
    );

    expect(screen.getByText("Mohammad Abdul Karim")).toBeInTheDocument();
    expect(screen.getByText("ID: EMP-2026-005")).toBeInTheDocument();
    expect(screen.getByText(/EIIN: 134582/)).toBeInTheDocument();
    expect(screen.getByText("৳47,000.00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /print/i })).toBeInTheDocument();
  });
});
