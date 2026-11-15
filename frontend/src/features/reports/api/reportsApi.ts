import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import { useAuthStore } from "@/features/auth/store/authStore";

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

// ---------------------------------------------------------------------------
// 1. AUDIT & ACTIVITY LOG TYPES
// ---------------------------------------------------------------------------
export type AuditActionType =
  | "create"
  | "update"
  | "delete"
  | "soft_delete"
  | "login"
  | "logout"
  | "login_failed"
  | "role_change"
  | "permission_change"
  | "approve"
  | "reject"
  | "override"
  | "export"
  | "consent_change"
  | "payment";

export interface AuditLog {
  id: string;
  institution?: string | null;
  actor?: string | null;
  actor_username: string;
  action: AuditActionType;
  module: string;
  target_model: string;
  target_object_id: string;
  target_repr: string;
  before_data: Record<string, unknown>;
  after_data: Record<string, unknown>;
  changed_fields: string[];
  ip_address?: string | null;
  user_agent: string;
  request_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ActivityLog {
  id: string;
  institution?: string | null;
  actor?: string | null;
  actor_username: string;
  activity_type: string;
  module: string;
  description: string;
  ip_address?: string | null;
  user_agent: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ---------------------------------------------------------------------------
// 2. REPORT BUILDER & EXPORTS TYPES
// ---------------------------------------------------------------------------
export type ReportDatasetType =
  | "students"
  | "daily_attendance"
  | "fee_invoices"
  | "fee_payments"
  | "exam_results";

export type ExportFormatType = "csv" | "xlsx" | "pdf";
export type ExportJobStatusType = "pending" | "processing" | "completed" | "failed";

export interface ReportDefinition {
  id: string;
  institution?: string;
  name: string;
  dataset: ReportDatasetType;
  selected_columns: string[];
  filters: Record<string, unknown>;
  default_format: ExportFormatType;
  created_by?: string | null;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReportExportJob {
  id: string;
  institution?: string;
  definition?: string | null;
  dataset: ReportDatasetType;
  selected_columns: string[];
  filters: Record<string, unknown>;
  export_format: ExportFormatType;
  status: ExportJobStatusType;
  file?: string | null;
  row_count: number;
  expires_at?: string | null;
  requested_by?: string | null;
  error_message?: string;
  created_at: string;
}

export interface CreateReportDefinitionInput {
  name: string;
  dataset: ReportDatasetType;
  selected_columns: string[];
  filters?: Record<string, unknown>;
  default_format: ExportFormatType;
  is_shared?: boolean;
}

export interface RunReportExportInput {
  dataset: ReportDatasetType;
  selected_columns?: string[];
  filters?: Record<string, unknown>;
  export_format: ExportFormatType;
}

// ---------------------------------------------------------------------------
// 3. BULK IMPORTS TYPES
// ---------------------------------------------------------------------------
export type BulkImportTargetType = "students" | "staff";
export type BulkImportStatusType = "validated" | "committed" | "failed";

export interface BulkImportJob {
  id: string;
  institution?: string;
  target_type: BulkImportTargetType;
  status: BulkImportStatusType;
  file: string;
  dry_run: boolean;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  errors_summary: Array<{ row: number; error: string; field?: string; data?: Record<string, unknown> }>;
  uploaded_by?: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// DATASET COLUMN & FILTER DEFINITIONS
// ---------------------------------------------------------------------------
export const DATASET_SPEC: Record<
  ReportDatasetType,
  { label: string; columns: { key: string; label: string }[]; filterFields: { key: string; label: string; type: "text" | "select" | "boolean"; options?: string[] }[] }
> = {
  students: {
    label: "Students Directory",
    columns: [
      { key: "student_id", label: "Student ID" },
      { key: "name_en", label: "Full Name (English)" },
      { key: "name_bn", label: "Full Name (Bangla)" },
      { key: "gender", label: "Gender" },
      { key: "dob", label: "Date of Birth" },
      { key: "admission_date", label: "Admission Date" },
      { key: "status", label: "Enrollment Status" },
    ],
    filterFields: [
      { key: "gender", label: "Gender", type: "select", options: ["male", "female", "other"] },
      { key: "status", label: "Status", type: "select", options: ["active", "graduated", "transferred", "suspended"] },
    ],
  },
  daily_attendance: {
    label: "Daily Attendance",
    columns: [
      { key: "date", label: "Date" },
      { key: "user_type", label: "User Type" },
      { key: "status", label: "Status" },
      { key: "minutes_late", label: "Minutes Late" },
      { key: "total_minutes", label: "Total Working Minutes" },
    ],
    filterFields: [
      { key: "user_type", label: "User Type", type: "select", options: ["student", "staff"] },
      { key: "status", label: "Status", type: "select", options: ["present", "absent", "late", "half_day"] },
    ],
  },
  fee_invoices: {
    label: "Fee Invoices & Dues",
    columns: [
      { key: "invoice_number", label: "Invoice No" },
      { key: "title", label: "Invoice Title" },
      { key: "billing_year", label: "Billing Year" },
      { key: "billing_month", label: "Billing Month" },
      { key: "total_payable", label: "Total Payable" },
      { key: "paid_amount", label: "Paid Amount" },
      { key: "due_amount", label: "Due Amount" },
      { key: "status", label: "Payment Status" },
      { key: "due_date", label: "Due Date" },
    ],
    filterFields: [
      { key: "status", label: "Status", type: "select", options: ["issued", "partially_paid", "paid", "overdue", "cancelled"] },
    ],
  },
  fee_payments: {
    label: "Fee Collections & POS",
    columns: [
      { key: "payment_method", label: "Payment Method" },
      { key: "amount", label: "Amount" },
      { key: "status", label: "Transaction Status" },
      { key: "transaction_id", label: "Transaction / Ref ID" },
      { key: "payment_date", label: "Payment Date" },
    ],
    filterFields: [
      { key: "payment_method", label: "Method", type: "select", options: ["cash", "bkash", "nagad", "rocket", "bank_transfer", "sslcommerz"] },
      { key: "status", label: "Status", type: "select", options: ["successful", "pending", "failed", "reversed"] },
    ],
  },
  exam_results: {
    label: "Examination Results & GPA",
    columns: [
      { key: "total_marks", label: "Total Marks" },
      { key: "gpa", label: "GPA" },
      { key: "letter_grade", label: "Letter Grade" },
      { key: "status", label: "Result Status" },
      { key: "is_passed", label: "Passed Flag" },
    ],
    filterFields: [
      { key: "is_passed", label: "Passed", type: "select", options: ["true", "false"] },
    ],
  },
};

// ---------------------------------------------------------------------------
// API METHODS
// ---------------------------------------------------------------------------
export const reportsApi = {
  // 1. Audit Logs
  getAuditLogs: async (params?: {
    action?: string;
    module?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResult<AuditLog>> => {
    const res = await apiClient.GET("/api/v1/audit/logs/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<AuditLog>>(res);
  },

  getAuditLog: async (id: string): Promise<AuditLog> => {
    const res = await apiClient.GET("/api/v1/audit/logs/{id}/", {
      params: { path: { id } },
    });
    return checkResponse<AuditLog>(res);
  },

  // 2. Activity Logs
  getActivityLogs: async (params?: {
    activity_type?: string;
    module?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResult<ActivityLog>> => {
    const res = await apiClient.GET("/api/v1/audit/activities/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<ActivityLog>>(res);
  },

  // 3. Report Definitions
  getReportDefinitions: async (params?: {
    dataset?: string;
    search?: string;
  }): Promise<PaginatedResult<ReportDefinition>> => {
    const res = await apiClient.GET("/api/v1/reports/definitions/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<ReportDefinition>>(res);
  },

  createReportDefinition: async (data: CreateReportDefinitionInput): Promise<ReportDefinition> => {
    const res = await apiClient.POST("/api/v1/reports/definitions/", {
      body: data as never,
    });
    return checkResponse<ReportDefinition>(res);
  },

  exportReportDefinition: async (id: string, export_format?: ExportFormatType): Promise<ReportExportJob> => {
    const res = await apiClient.POST("/api/v1/reports/definitions/{id}/export/", {
      params: { path: { id } },
      body: { export_format } as never,
    });
    return checkResponse<ReportExportJob>(res);
  },

  // 4. Report Exports
  getReportExports: async (params?: {
    dataset?: string;
    export_format?: string;
    status?: string;
    page?: number;
  }): Promise<PaginatedResult<ReportExportJob>> => {
    const res = await apiClient.GET("/api/v1/reports/exports/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<ReportExportJob>>(res);
  },

  runReportExport: async (data: RunReportExportInput): Promise<ReportExportJob> => {
    const res = await apiClient.POST("/api/v1/reports/exports/run/", {
      body: data as never,
    });
    return checkResponse<ReportExportJob>(res);
  },

  downloadReportExport: async (id: string): Promise<Blob> => {
    const token = useAuthStore.getState().accessToken;
    const response = await fetch(`/api/v1/reports/exports/${id}/download/`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      throw new Error("Failed to download export file");
    }
    return response.blob();
  },

  // 5. Bulk Imports
  getBulkImports: async (params?: {
    target_type?: string;
    status?: string;
    dry_run?: boolean;
    page?: number;
  }): Promise<PaginatedResult<BulkImportJob>> => {
    const res = await apiClient.GET("/api/v1/reports/imports/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<BulkImportJob>>(res);
  },

  downloadBulkImportTemplate: async (target_type: string): Promise<Blob> => {
    const token = useAuthStore.getState().accessToken;
    const response = await fetch(`/api/v1/reports/imports/template/?target_type=${target_type}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      throw new Error("Failed to download CSV template");
    }
    return response.blob();
  },

  uploadBulkImport: async (target_type: string, file: File, dry_run: boolean): Promise<BulkImportJob> => {
    const token = useAuthStore.getState().accessToken;
    const formData = new FormData();
    formData.append("target_type", target_type);
    formData.append("file", file);
    formData.append("dry_run", dry_run ? "true" : "false");

    const response = await fetch("/api/v1/reports/imports/upload/", {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!response.ok) {
      const err: unknown = await response.json().catch(() => ({}));
      throw parseApiError(response.status, err);
    }
    return response.json() as Promise<BulkImportJob>;
  },
};
