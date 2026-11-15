import { z } from "zod";

export const feeHeadSchema = z.object({
  code: z.string().min(2, "Code must be at least 2 characters").max(20),
  name_en: z.string().min(2, "English name is required").max(100),
  name_bn: z.string().min(2, "Bangla name is required").max(100),
  fee_type: z.enum([
    "tuition",
    "exam",
    "admission",
    "session",
    "transport",
    "hostel",
    "lab",
    "library",
    "other",
  ]),
  recurrence: z.enum(["one_time", "monthly", "term", "annual"]),
  is_optional: z.boolean(),
  is_refundable: z.boolean(),
  is_active: z.boolean(),
  description: z.string().optional(),
});

export type FeeHeadFormData = z.infer<typeof feeHeadSchema>;

export const feeStructureSchema = z.object({
  session: z.string().min(1, "Session is required"),
  class_level: z.string().min(1, "Class is required"),
  name: z.string().min(2, "Structure name is required"),
  group: z.string().optional().nullable(),
  is_active: z.boolean(),
});

export type FeeStructureFormData = z.infer<typeof feeStructureSchema>;

export const feeStructureItemSchema = z.object({
  fee_head: z.string().min(1, "Fee head is required"),
  amount: z.string().min(1, "Amount is required"),
  due_day: z.number().min(1).max(31),
  applicable_months: z.array(z.number()),
});

export type FeeStructureItemFormData = z.infer<typeof feeStructureItemSchema>;

export const counterPaymentSchema = z.object({
  student_id: z.string().min(1, "Student selection is required"),
  invoice_id: z.string().optional().nullable(),
  amount: z.string().min(1, "Amount is required"),
  payment_method: z.enum(["cash", "bkash", "nagad", "rocket", "bank", "card"]),
  bank_name: z.string().optional(),
  cheque_no: z.string().optional(),
  pos_approval_code: z.string().optional(),
  notes: z.string().optional(),
});

export type CounterPaymentFormData = z.infer<typeof counterPaymentSchema>;

export const bulkInvoiceGenerateSchema = z.object({
  session_id: z.string().min(1, "Session is required"),
  class_level_id: z.string().min(1, "Class is required"),
  section_id: z.string().optional().nullable(),
  billing_month: z.number().min(1).max(12).optional().nullable(),
  billing_year: z.number().min(2020).max(2035),
  invoice_type: z.enum(["monthly", "term", "annual", "admission", "custom"]),
  due_date: z.string().optional().nullable(),
  as_issued: z.boolean(),
});

export type BulkInvoiceGenerateFormData = z.infer<typeof bulkInvoiceGenerateSchema>;
