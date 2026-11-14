import { z } from "zod";

export const loginSchema = z.object({
  identifier: z
    .string()
    .min(1, "validation.identifierRequired"),
  password: z
    .string()
    .min(1, "validation.passwordRequired"),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const otpRequestSchema = z.object({
  phone: z
    .string()
    .min(1, "validation.phoneRequired")
    .regex(/^(\+8801|01)[3-9]\d{8}$/, "validation.phoneInvalid"),
});

export type OtpRequestFormData = z.infer<typeof otpRequestSchema>;

export const otpVerifySchema = z.object({
  phone: z.string().min(1),
  code: z
    .string()
    .length(6, "validation.otpCodeLength")
    .regex(/^\d+$/, "validation.otpCodeDigits"),
});

export type OtpVerifyFormData = z.infer<typeof otpVerifySchema>;

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "validation.oldPasswordRequired"),
    new_password: z
      .string()
      .min(8, "validation.newPasswordMinLength")
      .regex(/[A-Z]/, "validation.newPasswordUppercase")
      .regex(/[0-9]/, "validation.newPasswordNumber"),
    confirm_password: z.string().min(1, "validation.confirmPasswordRequired"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "validation.passwordsMustMatch",
    path: ["confirm_password"],
  });

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;

export const profileUpdateSchema = z.object({
  language_preference: z.enum(["bn", "en"]),
});

export type ProfileUpdateFormData = z.infer<typeof profileUpdateSchema>;
