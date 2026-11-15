import { z } from "zod";

export const sendDirectSmsSchema = z.object({
  phone: z.string().regex(/^(\+88)?01[3-9]\d{8}$/, "Valid Bangladeshi mobile number required (01XXXXXXXXX)"),
  message: z.string().min(1, "Message text cannot be empty"),
  gateway_id: z.string().optional(),
});

export type SendDirectSmsFormData = z.infer<typeof sendDirectSmsSchema>;

export const sendCampaignSmsSchema = z.object({
  audience: z.enum(["all_guardians", "all_staff", "class_students", "custom_numbers"]),
  class_level_id: z.string().optional(),
  section_id: z.string().optional(),
  custom_numbers: z.string().optional(),
  message: z.string().min(1, "Message text cannot be empty"),
  gateway_id: z.string().optional(),
});

export type SendCampaignSmsFormData = z.infer<typeof sendCampaignSmsSchema>;

export const noticeSchema = z.object({
  title_en: z.string().min(3, "Title must be at least 3 characters").max(255),
  title_bn: z.string().max(255).optional(),
  content_en: z.string().min(5, "Content is required"),
  content_bn: z.string().optional(),
  category: z.enum(["general", "academic", "exam", "fee", "holiday", "emergency"]),
  target_audience: z.enum(["all", "students", "guardians", "teachers", "staff", "specific_class"]),
  target_class_level: z.string().nullable().optional(),
  target_section: z.string().nullable().optional(),
  is_pinned: z.boolean(),
  is_published: z.boolean(),
  publish_date: z.string().optional(),
  expiry_date: z.string().nullable().optional(),
});

export type NoticeFormData = z.infer<typeof noticeSchema>;

export const emergencyAlertSchema = z.object({
  title: z.string().min(3, "Alert title is required").max(200),
  message_bn: z.string().min(5, "Bangla emergency alert message is required"),
  message_en: z.string().optional(),
  severity: z.enum(["warning", "critical", "disaster"]),
  channels: z.array(z.enum(["sms", "push", "email", "in_app"])).min(1, "Select at least one broadcast channel"),
});

export type EmergencyAlertFormData = z.infer<typeof emergencyAlertSchema>;

export const notificationTemplateSchema = z.object({
  name: z.string().min(3, "Template name is required").max(150),
  code: z.string().min(2, "Event code is required").max(50),
  channel: z.enum(["sms", "push", "email", "in_app", "all"]),
  subject_template: z.string().optional(),
  body_template_en: z.string().min(5, "English template body is required"),
  body_template_bn: z.string().min(5, "Bangla template body is required"),
  is_active: z.boolean(),
});

export type NotificationTemplateFormData = z.infer<typeof notificationTemplateSchema>;
