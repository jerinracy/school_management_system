import { z } from "zod";

const BD_PHONE_REGEX = /^(?:\+8801|8801|01)[3-9]\d{8}$/;

export const studentCreateSchema = z.object({
  name_en: z.string().min(2, "validation.nameEnRequired").max(100),
  name_bn: z.string().min(2, "validation.nameBnRequired").max(100),
  dob: z.string().min(1, "validation.dobRequired"),
  gender: z.enum(["male", "female", "other"]),
  blood_group: z.enum(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", ""]).optional(),
  religion: z.enum(["islam", "hinduism", "buddhism", "christianity", "other"]),
  birth_reg_no: z
    .string()
    .trim()
    .refine(
      (val) => !val || (/^\d{17}$/.test(val)),
      "validation.birthRegNoLength",
    )
    .optional(),
  present_address: z.string().min(2, "validation.addressRequired").max(255),
  permanent_address: z.string().max(255).optional(),
  emergency_contact_name: z.string().min(2, "validation.contactNameRequired").max(100),
  emergency_contact_phone: z
    .string()
    .trim()
    .refine(
      (val) => !val || BD_PHONE_REGEX.test(val),
      "validation.phoneInvalid",
    ),

  // Academic initial enrollment
  session_id: z.string().min(1, "validation.sessionRequired"),
  class_level_id: z.string().min(1, "validation.classRequired"),
  section_id: z.string().min(1, "validation.sectionRequired"),
  roll_no: z.coerce.number().min(1, "validation.rollNoRequired"),
  group_id: z.string().optional(),
  shift_id: z.string().optional(),
});

export type StudentCreateFormData = z.infer<typeof studentCreateSchema>;

export const guardianCreateSchema = z.object({
  name_en: z.string().min(2, "validation.nameEnRequired").max(100),
  name_bn: z.string().min(2, "validation.nameBnRequired").max(100),
  phone: z
    .string()
    .trim()
    .refine((val) => BD_PHONE_REGEX.test(val), "validation.phoneInvalid"),
  nid_number: z.string().trim().max(20).optional(),
  occupation: z.string().max(100).optional(),
  present_address: z.string().max(255).optional(),
});

export type GuardianCreateFormData = z.infer<typeof guardianCreateSchema>;

export const linkGuardianSchema = z.object({
  guardian_id: z.string().min(1, "validation.guardianRequired"),
  relation: z.enum(["father", "mother", "legal_guardian", "other"]),
  is_primary: z.boolean().default(false),
  can_pickup: z.boolean().default(true),
  receives_sms: z.boolean().default(true),
  financial_responsible: z.boolean().default(false),
});

export type LinkGuardianFormData = z.infer<typeof linkGuardianSchema>;
