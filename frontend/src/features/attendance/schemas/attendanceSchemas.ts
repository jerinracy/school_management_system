import { z } from "zod";

export const attendanceRecomputeSchema = z.object({
  start_date: z.string().min(1, "validation.startDateRequired"),
  end_date: z.string().min(1, "validation.endDateRequired"),
  user_type: z.enum(["all", "student", "staff"]).default("all"),
});

export type AttendanceRecomputeFormData = z.infer<typeof attendanceRecomputeSchema>;

export const correctionDecideSchema = z.object({
  approved: z.boolean(),
  rejection_reason: z.string().optional(),
});

export type CorrectionDecideFormData = z.infer<typeof correctionDecideSchema>;

export const attendancePolicyFormSchema = z.object({
  name: z.string().min(2, "validation.nameRequired").max(100),
  user_type: z.enum(["student", "staff", "all"]).default("student"),
  start_time: z.string().min(1, "validation.startTimeRequired"),
  end_time: z.string().min(1, "validation.endTimeRequired"),
  grace_minutes: z.coerce.number().min(0).default(15),
  late_threshold_minutes: z.coerce.number().min(0).default(30),
  half_day_threshold_minutes: z.coerce.number().min(0).default(120),
  early_leave_threshold_minutes: z.coerce.number().min(0).default(30),
  min_work_duration_minutes: z.coerce.number().min(0).default(240),
  weekend_days: z.array(z.string()).default(["friday", "saturday"]),
  is_active: z.boolean().default(true),
});

export type AttendancePolicyFormData = z.infer<typeof attendancePolicyFormSchema>;
