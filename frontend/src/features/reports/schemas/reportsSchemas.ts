import { z } from "zod";

export const reportDefinitionSchema = z.object({
  name: z.string().min(3, "Report name must be at least 3 characters").max(150),
  dataset: z.enum([
    "students",
    "daily_attendance",
    "fee_invoices",
    "fee_payments",
    "exam_results",
  ]),
  selected_columns: z.array(z.string()).min(1, "Select at least one column"),
  default_format: z.enum(["csv", "xlsx", "pdf"]),
  is_shared: z.boolean().default(false),
});

export type ReportDefinitionFormData = z.infer<typeof reportDefinitionSchema>;

export const quickExportSchema = z.object({
  dataset: z.enum([
    "students",
    "daily_attendance",
    "fee_invoices",
    "fee_payments",
    "exam_results",
  ]),
  export_format: z.enum(["csv", "xlsx", "pdf"]),
});

export type QuickExportFormData = z.infer<typeof quickExportSchema>;

export const bulkImportUploadSchema = z.object({
  target_type: z.enum(["students", "staff"]),
  dry_run: z.boolean().default(true),
});

export type BulkImportUploadFormData = z.infer<typeof bulkImportUploadSchema>;
