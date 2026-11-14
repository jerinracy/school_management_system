import { z } from "zod";

const BD_PHONE_REGEX = /^(?:\+8801|8801|01)[3-9]\d{8}$/;

export const staffCreateSchema = z.object({
  full_name_en: z.string().min(2, "validation.nameEnRequired").max(100),
  full_name_bn: z.string().min(2, "validation.nameBnRequired").max(100),
  employee_id: z.string().max(32).optional(),
  phone: z
    .string()
    .trim()
    .refine((val) => BD_PHONE_REGEX.test(val), "validation.phoneInvalid"),
  alt_phone: z
    .string()
    .trim()
    .refine((val) => !val || BD_PHONE_REGEX.test(val), "validation.phoneInvalid")
    .optional(),
  email: z.string().email("validation.emailInvalid").optional().or(z.literal("")),
  dob: z.string().min(1, "validation.dobRequired"),
  gender: z.enum(["male", "female", "other"]),
  blood_group: z.enum(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", ""]).optional(),
  nid: z
    .string()
    .trim()
    .refine(
      (val) => !val || /^(?:\d{10}|\d{13}|\d{17})$/.test(val),
      "validation.nidInvalid",
    )
    .optional(),
  department: z.string().min(1, "validation.departmentRequired"),
  designation: z.string().min(1, "validation.designationRequired"),
  staff_type: z.enum(["admin", "teacher", "support", "driver", "security", "other"]),
  joining_date: z.string().min(1, "validation.joiningDateRequired"),
  confirmation_date: z.string().optional(),
  tin_number: z.string().max(32).optional(),
  is_mpo: z.boolean().default(false),
  mpo_index_number: z.string().max(32).optional(),
  present_address: z.string().min(2, "validation.addressRequired").max(255),
  permanent_address: z.string().max(255).optional(),
  emergency_contact_name: z.string().min(2, "validation.contactNameRequired").max(100),
  emergency_contact_phone: z
    .string()
    .trim()
    .refine((val) => BD_PHONE_REGEX.test(val), "validation.phoneInvalid"),
  emergency_contact_relation: z.string().max(50).optional(),
});

export type StaffCreateFormData = z.infer<typeof staffCreateSchema>;

export const departmentSchema = z.object({
  name: z.string().min(2, "validation.nameRequired").max(100),
  code: z.string().min(1, "validation.codeRequired").max(20),
  description: z.string().max(255).optional(),
  head_of_department: z.string().optional(),
});

export type DepartmentFormData = z.infer<typeof departmentSchema>;

export const designationSchema = z.object({
  title: z.string().min(2, "validation.titleRequired").max(100),
  title_bn: z.string().max(100).optional(),
  code: z.string().min(1, "validation.codeRequired").max(20),
  rank_order: z.coerce.number().min(1).default(1),
  role_category: z.enum(["admin", "teacher", "support", "driver", "security", "other"]).default("teacher"),
});

export type DesignationFormData = z.infer<typeof designationSchema>;

export const leaveApplySchema = z.object({
  staff_id: z.string().optional(),
  leave_type_id: z.string().min(1, "validation.leaveTypeRequired"),
  session_id: z.string().optional(),
  start_date: z.string().min(1, "validation.startDateRequired"),
  end_date: z.string().min(1, "validation.endDateRequired"),
  reason: z.string().min(5, "validation.reasonRequired").max(500),
  emergency_contact_phone: z
    .string()
    .trim()
    .refine((val) => !val || BD_PHONE_REGEX.test(val), "validation.phoneInvalid")
    .optional(),
});

export type LeaveApplyFormData = z.infer<typeof leaveApplySchema>;
