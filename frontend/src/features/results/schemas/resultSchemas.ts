import { z } from "zod";

export const resultPublishSchema = z.object({
  exam_id: z.string().min(1, "Exam ID is required"),
  is_visible_to_guardians: z.boolean().default(true),
  is_visible_to_students: z.boolean().default(true),
  allow_public_search: z.boolean().default(false),
  remarks: z.string().optional(),
});

export type ResultPublishFormData = z.infer<typeof resultPublishSchema>;

export const reportCardGenerateSchema = z.object({
  exam_result_id: z.string().min(1, "Result ID is required"),
  template_style: z.enum(["default_bd", "modern"]).default("default_bd"),
});

export type ReportCardGenerateFormData = z.infer<typeof reportCardGenerateSchema>;

export const tabulationSheetGenerateSchema = z.object({
  exam: z.string().min(1, "Exam is required"),
  class_level: z.string().min(1, "Class is required"),
  section: z.string().optional(),
  file_format: z.enum(["pdf", "excel", "csv"]).default("pdf"),
});

export type TabulationSheetGenerateFormData = z.infer<typeof tabulationSheetGenerateSchema>;
