import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";

export interface FeeHead {
  id: string;
  code: string;
  name_en: string;
  name_bn: string;
  fee_type: "tuition" | "exam" | "admission" | "session" | "transport" | "hostel" | "lab" | "library" | "other";
  recurrence: "one_time" | "monthly" | "term" | "annual";
  is_optional: boolean;
  is_refundable: boolean;
  is_active: boolean;
  account_code?: string;
  description?: string;
  created_at: string;
}

export interface FeeStructureItem {
  id: string;
  fee_head: string;
  fee_head_name: string;
  fee_head_code: string;
  amount: string;
  due_day: number;
  applicable_months: number[];
}

export interface FeeStructure {
  id: string;
  session: string;
  session_name: string;
  class_level: string;
  class_level_name: string;
  group?: string | null;
  name: string;
  is_active: boolean;
  items: FeeStructureItem[];
  created_at: string;
}

export interface InvoiceLine {
  id: string;
  fee_head: string;
  fee_head_code: string;
  fee_head_name: string;
  description: string;
  amount: string;
  waiver_amount: string;
  fine_amount: string;
  payable_amount: string;
  paid_amount: string;
}

export interface InvoiceItem {
  id: string;
  invoice_number: string;
  student: string;
  student_code: string;
  student_name: string;
  session: string;
  session_name: string;
  invoice_type: "monthly" | "term" | "annual" | "admission" | "custom";
  title: string;
  billing_month?: number | null;
  billing_year?: number;
  subtotal_amount: string;
  waiver_amount: string;
  fine_amount: string;
  total_payable: string;
  paid_amount: string;
  due_amount: string;
  status: "draft" | "issued" | "partially_paid" | "paid" | "overdue" | "cancelled";
  issue_date?: string | null;
  due_date?: string | null;
  paid_date?: string | null;
  cancellation_reason?: string;
  lines?: InvoiceLine[];
  created_at: string;
}

export interface DueListItem {
  student_id: string;
  student_name_en: string;
  student_name_bn: string;
  roll_no: number | null;
  class_name: string;
  section_name: string;
  unpaid_invoice_count: number;
  total_due_amount: string;
  oldest_overdue_date: string | null;
}

export interface MoneyReceiptItem {
  id: string;
  receipt_number: string;
  payment: string;
  student: string;
  student_name_en: string;
  student_name_bn: string;
  total_amount: string;
  issued_at: string;
  issued_by_name?: string | null;
  pdf_receipt?: string | null;
  is_cancelled: boolean;
  created_at: string;
}

export interface PaymentItem {
  id: string;
  student: string;
  student_name_en: string;
  invoice?: string | null;
  invoice_number?: string | null;
  payment_method: "cash" | "bkash" | "nagad" | "rocket" | "bank" | "card" | "sslcommerz";
  amount: string;
  status: "pending" | "completed" | "failed" | "refunded";
  transaction_id?: string;
  payment_date: string;
  received_by_name?: string | null;
  receipt_number?: string | null;
  notes?: string;
  created_at: string;
}

export interface WaiverRuleItem {
  id: string;
  name: string;
  category: "merit" | "sibling" | "freedom_fighter" | "poor_fund" | "staff_child" | "special";
  discount_type: "percentage" | "fixed_amount";
  discount_value: string;
  max_discount_amount?: string | null;
  is_active: boolean;
  description?: string;
}

export interface StudentWaiverItem {
  id: string;
  student: string;
  student_code: string;
  student_name: string;
  waiver_rule?: string | null;
  waiver_rule_name?: string | null;
  title: string;
  discount_type: "percentage" | "fixed_amount";
  discount_value: string;
  status: "pending" | "approved" | "rejected" | "revoked";
  approved_by_name?: string | null;
  approved_at?: string | null;
  rejection_reason?: string;
  valid_from: string;
  valid_to: string;
  created_at: string;
}

function checkResponse<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

export const feesApi = {
  // Fee Heads
  async getFeeHeads(params?: { search?: string; fee_type?: string; is_active?: boolean; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/heads/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async createFeeHead(payload: Partial<FeeHead>) {
    const res = await apiClient.POST("/api/v1/fees/heads/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  // Fee Structures
  async getFeeStructures(params?: { session?: string; class_level?: string; is_active?: boolean; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/structures/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async getFeeStructure(id: string) {
    const res = await apiClient.GET("/api/v1/fees/structures/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async createFeeStructure(payload: {
    session: string;
    class_level: string;
    name: string;
    group?: string | null;
    is_active?: boolean;
  }) {
    const res = await apiClient.POST("/api/v1/fees/structures/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async addStructureItem(structureId: string, item: {
    fee_head: string;
    amount: string | number;
    due_day?: number;
    applicable_months?: number[];
  }) {
    const res = await apiClient.POST("/api/v1/fees/structures/{id}/items/", {
      params: { path: { id: structureId } },
      body: item as never,
    });
    return checkResponse(res);
  },

  // Invoices
  async getInvoices(params?: {
    student?: string;
    session?: string;
    status?: string;
    invoice_type?: string;
    search?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/fees/invoices/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async getInvoice(id: string) {
    const res = await apiClient.GET("/api/v1/fees/invoices/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async generateSingleInvoice(payload: {
    student_id: string;
    session_id: string;
    invoice_type?: string;
    billing_month?: number | null;
    billing_year?: number;
    due_date?: string | null;
    title?: string;
  }) {
    const res = await apiClient.POST("/api/v1/fees/invoices/generate-single/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async bulkPreviewInvoices(payload: {
    session_id: string;
    class_level_id: string;
    section_id?: string | null;
    billing_month?: number | null;
    billing_year?: number;
    invoice_type?: string;
  }) {
    const res = await apiClient.POST("/api/v1/fees/invoices/bulk-preview/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async bulkGenerateInvoices(payload: {
    session_id: string;
    class_level_id: string;
    section_id?: string | null;
    billing_month?: number | null;
    billing_year?: number;
    invoice_type?: string;
    due_date?: string | null;
    as_issued?: boolean;
  }) {
    const res = await apiClient.POST("/api/v1/fees/invoices/bulk-generate/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async cancelInvoice(id: string, reason: string) {
    const res = await apiClient.POST("/api/v1/fees/invoices/{id}/cancel/", {
      params: { path: { id } },
      body: { reason } as never,
    });
    return checkResponse(res);
  },

  // Counter Collection & Payments
  async recordCounterPayment(payload: {
    student_id: string;
    invoice_id?: string | null;
    amount: string | number;
    payment_method: string;
    bank_name?: string;
    cheque_no?: string;
    pos_approval_code?: string;
    notes?: string;
  }) {
    const res = await apiClient.POST("/api/v1/fees/payments/counter/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getPayments(params?: { student?: string; payment_method?: string; status?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/payments/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async getDailyCollection(date?: string) {
    const res = await apiClient.GET("/api/v1/fees/payments/daily-collection/", {
      params: date ? { query: { date } as never } : undefined,
    });
    return checkResponse(res);
  },

  // Money Receipts
  async getMoneyReceipts(params?: { student?: string; search?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/receipts/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async getMoneyReceipt(id: string) {
    const res = await apiClient.GET("/api/v1/fees/receipts/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  // Due List
  async getDueList(params?: { class_level?: string; section?: string; min_days_overdue?: number; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/due-list/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  // Waivers
  async getWaiverRules(params?: { is_active?: boolean; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/waiver-rules/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async createWaiverRule(payload: Partial<WaiverRuleItem>) {
    const res = await apiClient.POST("/api/v1/fees/waiver-rules/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async getStudentWaivers(params?: { student?: string; status?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/fees/student-waivers/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },

  async approveStudentWaiver(id: string) {
    const res = await apiClient.POST("/api/v1/fees/student-waivers/{id}/approve/", {
      params: { path: { id } },
      body: {} as never,
    });
    return checkResponse(res);
  },

  async rejectStudentWaiver(id: string, reason?: string) {
    const res = await apiClient.POST("/api/v1/fees/student-waivers/{id}/reject/", {
      params: { path: { id } },
      body: { reason: reason || "" } as never,
    });
    return checkResponse(res);
  },
};
