import { z } from "zod";

export const generatePayrollRunSchema = z.object({
  year: z.number().int().min(2020).max(2050),
  month: z.number().int().min(1).max(12),
  title: z.string().optional(),
  working_days_in_month: z.number().int().min(1).max(31).optional(),
  absence_deduction_basis: z.enum(["basic", "gross"]),
});

export type GeneratePayrollRunFormData = z.infer<typeof generatePayrollRunSchema>;

export const applyBonusSchema = z.object({
  bonus_title: z.string().min(2, "Bonus title is required"),
  bonus_type: z.enum(["percentage", "fixed"]),
  percentage_of_basic: z.number().min(0).max(200).optional(),
  fixed_amount: z.number().min(0).optional(),
  staff_type: z.string().optional(),
});

export type ApplyBonusFormData = z.infer<typeof applyBonusSchema>;

export const createSalaryStructureSchema = z.object({
  code: z.string().min(2, "Code must be at least 2 characters").max(40),
  name: z.string().min(2, "Name is required").max(150),
  name_bn: z.string().max(150).optional(),
  description: z.string().optional(),
  is_active: z.boolean(),
});

export type CreateSalaryStructureFormData = z.infer<typeof createSalaryStructureSchema>;

export const staffSalaryProfileSchema = z.object({
  structure: z.string().nullable().optional(),
  basic_salary: z.number().min(0, "Basic salary must be non-negative"),
  mpo_portion: z.number().min(0).optional(),
  institutional_portion: z.number().min(0).optional(),
  payment_method: z.enum(["bank_transfer", "cash", "cheque", "mfs"]),
  bank_name: z.string().optional(),
  bank_branch: z.string().optional(),
  bank_account_number: z.string().optional(),
  bank_routing_number: z.string().optional(),
  mfs_number: z.string().optional(),
  pf_enrolled: z.boolean(),
  pf_employee_percent: z.number().min(0).max(100).optional(),
});

export type StaffSalaryProfileFormData = z.infer<typeof staffSalaryProfileSchema>;

export const createStaffSalaryProfileSchema = staffSalaryProfileSchema.extend({
  staff: z.string().min(1, "Staff member is required"),
});

export type CreateStaffSalaryProfileFormData = z.infer<typeof createStaffSalaryProfileSchema>;

export const staffLoanSchema = z.object({
  staff: z.string().min(1, "Staff member is required"),
  loan_type: z.enum(["advance", "loan"]),
  principal_amount: z.number().positive("Principal amount must be greater than 0"),
  monthly_installment: z.number().positive("Monthly installment must be greater than 0"),
  disbursed_date: z.string().optional(),
  reason: z.string().optional(),
});

export type StaffLoanFormData = z.infer<typeof staffLoanSchema>;
