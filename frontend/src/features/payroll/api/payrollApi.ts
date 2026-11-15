import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";

export type ComponentType = "earning" | "deduction";
export type CalculationType = "fixed" | "percentage_of_basic" | "percentage_of_gross";
export type PaymentMethod = "bank_transfer" | "cash" | "cheque" | "mfs";
export type PayrollRunStatus = "draft" | "reviewed" | "approved" | "paid" | "locked";
export type AbsenceDeductionBasis = "basic" | "gross";
export type LoanType = "advance" | "loan";
export type LoanStatus = "active" | "completed" | "paused";

export interface SalaryComponent {
  id: string;
  code: string;
  name_en: string;
  name_bn?: string;
  component_type: ComponentType;
  calculation_type: CalculationType;
  default_value: string;
  is_taxable: boolean;
  is_system: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string;
}

export interface SalaryStructureLine {
  id: string;
  structure: string;
  component: string;
  component_code: string;
  component_name_en: string;
  component_type: string;
  calculation_type: CalculationType;
  value: string;
}

export interface SalaryStructure {
  id: string;
  code: string;
  name: string;
  name_bn?: string;
  description?: string;
  is_active: boolean;
  lines: SalaryStructureLine[];
  created_at: string;
}

export interface StaffSalaryProfile {
  id: string;
  staff: string;
  staff_employee_id: string;
  staff_name_en: string;
  staff_name_bn: string;
  structure?: string | null;
  structure_name?: string;
  basic_salary: string;
  mpo_portion?: string;
  institutional_portion?: string;
  payment_method: PaymentMethod;
  bank_name?: string;
  bank_branch?: string;
  bank_account_number?: string;
  bank_routing_number?: string;
  mfs_number?: string;
  pf_enrolled: boolean;
  pf_employee_percent?: string;
  effective_from?: string;
  created_at: string;
}

export interface StaffLoan {
  id: string;
  staff: string;
  staff_employee_id: string;
  staff_name_en: string;
  loan_type: LoanType;
  principal_amount: string;
  monthly_installment: string;
  total_recovered: string;
  remaining_balance: string;
  status: LoanStatus;
  disbursed_date?: string;
  reason?: string;
  approved_by?: string | null;
  created_at: string;
}

export interface PayrollRun {
  id: string;
  month: number;
  year: number;
  title: string;
  status: PayrollRunStatus;
  is_locked: boolean;
  working_days_in_month: number;
  absence_deduction_basis: AbsenceDeductionBasis;
  total_gross: string;
  total_deductions: string;
  total_net_pay: string;
  total_employer_pf: string;
  journal_entry: string | null;
  journal_entry_voucher_no: string;
  payslips_count: number;
  prepared_by: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
}

export interface PayslipLine {
  id: string;
  component: string | null;
  name_en: string;
  name_bn: string;
  line_type: "earning" | "deduction";
  amount: string;
  notes?: string;
}

export interface Payslip {
  id: string;
  payroll_run: string;
  month: number;
  year: number;
  run_status: string;
  staff: string;
  staff_employee_id: string;
  staff_name_en: string;
  staff_name_bn: string;
  working_days: number;
  present_days: string;
  late_days: number;
  half_days: number;
  paid_leave_days: string;
  unpaid_leave_days: string;
  absent_days: string;
  overtime_hours: string;
  basic_salary: string;
  overtime_amount: string;
  bonus_amount: string;
  gross_earnings: string;
  absence_deduction_amount: string;
  pf_employee_amount: string;
  pf_employer_amount: string;
  loan_deduction_amount: string;
  total_deductions: string;
  net_payable: string;
  payment_method: PaymentMethod;
  is_paid: boolean;
  paid_at: string | null;
  payment_reference: string;
  notes: string;
  lines: PayslipLine[];
  created_at: string;
  updated_at: string;
}

export interface PaginatedResult<T> {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
}

function checkResponse<T>(res: { data?: unknown; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

export const payrollApi = {
  // --- Salary Components ---
  async getComponents(params?: { component_type?: string; is_active?: boolean; search?: string }): Promise<PaginatedResult<SalaryComponent>> {
    const res = await apiClient.GET("/api/v1/payroll/components/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<SalaryComponent>>(res);
  },

  async seedDefaultComponents(): Promise<SalaryComponent[]> {
    const res = await apiClient.POST("/api/v1/payroll/components/seed_defaults/", {});
    return checkResponse<SalaryComponent[]>(res);
  },

  async createComponent(data: Partial<SalaryComponent>): Promise<SalaryComponent> {
    const res = await apiClient.POST("/api/v1/payroll/components/", {
      body: data as never,
    });
    return checkResponse<SalaryComponent>(res);
  },

  // --- Salary Structures ---
  async getStructures(params?: { is_active?: boolean; search?: string }): Promise<PaginatedResult<SalaryStructure>> {
    const res = await apiClient.GET("/api/v1/payroll/structures/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<SalaryStructure>>(res);
  },

  async getStructureDetail(id: string): Promise<SalaryStructure> {
    const res = await apiClient.GET("/api/v1/payroll/structures/{id}/", {
      params: { path: { id } },
    });
    return checkResponse<SalaryStructure>(res);
  },

  async seedDefaultStructures(): Promise<SalaryStructure[]> {
    const res = await apiClient.POST("/api/v1/payroll/structures/seed_defaults/", {});
    return checkResponse<SalaryStructure[]>(res);
  },

  async createStructure(data: {
    code: string;
    name: string;
    name_bn?: string;
    description?: string;
    is_active?: boolean;
    lines?: Array<{
      component: string;
      calculation_type: CalculationType;
      value: string;
    }>;
  }): Promise<SalaryStructure> {
    const res = await apiClient.POST("/api/v1/payroll/structures/", {
      body: data as never,
    });
    return checkResponse<SalaryStructure>(res);
  },

  // --- Staff Salary Profiles ---
  async getProfiles(params?: { structure?: string; search?: string; page?: number }): Promise<PaginatedResult<StaffSalaryProfile>> {
    const res = await apiClient.GET("/api/v1/payroll/profiles/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<StaffSalaryProfile>>(res);
  },

  async updateProfile(
    id: string,
    data: Partial<StaffSalaryProfile>
  ): Promise<StaffSalaryProfile> {
    const res = await apiClient.PATCH("/api/v1/payroll/profiles/{id}/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse<StaffSalaryProfile>(res);
  },

  // --- Staff Loans & Advances ---
  async getLoans(params?: { staff?: string; loan_type?: string; status?: string; search?: string }): Promise<PaginatedResult<StaffLoan>> {
    const res = await apiClient.GET("/api/v1/payroll/loans/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<StaffLoan>>(res);
  },

  async createLoan(data: {
    staff: string;
    loan_type: LoanType;
    principal_amount: string;
    monthly_installment: string;
    disbursed_date?: string;
    reason?: string;
  }): Promise<StaffLoan> {
    const res = await apiClient.POST("/api/v1/payroll/loans/", {
      body: data as never,
    });
    return checkResponse<StaffLoan>(res);
  },

  // --- Payroll Runs ---
  async getPayrollRuns(params?: { year?: number; month?: number; status?: string; is_locked?: boolean }): Promise<PaginatedResult<PayrollRun>> {
    const res = await apiClient.GET("/api/v1/payroll/runs/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<PayrollRun>>(res);
  },

  async getPayrollRunDetail(id: string): Promise<PayrollRun> {
    const res = await apiClient.GET("/api/v1/payroll/runs/{id}/", {
      params: { path: { id } },
    });
    return checkResponse<PayrollRun>(res);
  },

  async generatePayrollRun(data: {
    year: number;
    month: number;
    title?: string;
    working_days_in_month?: number;
    absence_deduction_basis: AbsenceDeductionBasis;
  }): Promise<PayrollRun> {
    const res = await apiClient.POST("/api/v1/payroll/runs/generate/", {
      body: data as never,
    });
    return checkResponse<PayrollRun>(res);
  },

  async applyBonus(
    runId: string,
    data: {
      bonus_title: string;
      percentage_of_basic?: string;
      fixed_amount?: string;
      staff_type?: string;
    }
  ): Promise<PayrollRun> {
    const res = await apiClient.POST("/api/v1/payroll/runs/{id}/apply_bonus/", {
      params: { path: { id: runId } },
      body: data as never,
    });
    return checkResponse<PayrollRun>(res);
  },

  async reviewRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.POST("/api/v1/payroll/runs/{id}/review/", {
      params: { path: { id: runId } },
    });
    return checkResponse<PayrollRun>(res);
  },

  async approveRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.POST("/api/v1/payroll/runs/{id}/approve/", {
      params: { path: { id: runId } },
    });
    return checkResponse<PayrollRun>(res);
  },

  async markRunPaid(runId: string, paymentReference?: string): Promise<PayrollRun> {
    const res = await apiClient.POST("/api/v1/payroll/runs/{id}/mark_paid/", {
      params: { path: { id: runId } },
      body: { payment_reference: paymentReference || "" } as never,
    });
    return checkResponse<PayrollRun>(res);
  },

  async lockRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.POST("/api/v1/payroll/runs/{id}/lock/", {
      params: { path: { id: runId } },
    });
    return checkResponse<PayrollRun>(res);
  },

  async postRunToAccounting(runId: string, paymentMethod?: string): Promise<{
    journal_entry_id: string;
    voucher_no: string;
    total_debit: string;
    total_credit: string;
    status: string;
  }> {
    const res = await apiClient.POST("/api/v1/payroll/runs/{id}/post_to_accounting/", {
      params: { path: { id: runId } },
      body: { payment_method: paymentMethod || "bank_transfer" } as never,
    });
    return checkResponse<{
      journal_entry_id: string;
      voucher_no: string;
      total_debit: string;
      total_credit: string;
      status: string;
    }>(res);
  },

  getBankAdviceUrl(runId: string, format: "xlsx" | "csv" = "xlsx"): string {
    return `/api/v1/payroll/runs/${runId}/bank_advice/?export_format=${format}`;
  },

  // --- Payslips ---
  async getPayslips(params?: {
    payroll_run?: string;
    staff?: string;
    is_paid?: boolean;
    payment_method?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResult<Payslip>> {
    const res = await apiClient.GET("/api/v1/payroll/payslips/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<Payslip>>(res);
  },

  async getPayslipDetail(id: string): Promise<Payslip> {
    const res = await apiClient.GET("/api/v1/payroll/payslips/{id}/", {
      params: { path: { id } },
    });
    return checkResponse<Payslip>(res);
  },

  getPayslipPdfUrl(id: string): string {
    return `/api/v1/payroll/payslips/${id}/pdf/`;
  },
};
