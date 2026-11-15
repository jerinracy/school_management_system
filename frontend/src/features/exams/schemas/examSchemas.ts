import { z } from "zod";

export const examFormSchema = z.object({
  name: z.string().min(2, "Exam name must be at least 2 characters"),
  exam_type: z.string().min(1, "Please select an exam type"),
  session: z.string().min(1, "Please select an academic session"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().min(1, "End date is required"),
  term: z.string().optional(),
  weightage: z.string().optional(),
  target_classes: z.array(z.string()).optional(),
});

export type ExamFormData = z.infer<typeof examFormSchema>;

export const examSubjectFormSchema = z.object({
  subject: z.string().min(1, "Subject is required"),
  class_level: z.string().min(1, "Class is required"),
  exam_date: z.string().optional(),
  start_time: z.string().optional(),
  end_time: z.string().optional(),
  full_marks: z.string().min(1, "Full marks is required"),
  pass_marks: z.string().min(1, "Pass marks is required"),
  creative_full_marks: z.string().optional(),
  creative_pass_marks: z.string().optional(),
  mcq_full_marks: z.string().optional(),
  mcq_pass_marks: z.string().optional(),
  practical_full_marks: z.string().optional(),
  practical_pass_marks: z.string().optional(),
  assigned_teacher: z.string().optional(),
});

export type ExamSubjectFormData = z.infer<typeof examSubjectFormSchema>;

export const bulkMarkEntryItemSchema = z.object({
  student_id: z.string(),
  creative_marks: z.number().nullable().optional(),
  mcq_marks: z.number().nullable().optional(),
  practical_marks: z.number().nullable().optional(),
  is_absent: z.boolean().default(false),
  reason: z.string().optional(),
});

export type BulkMarkEntryItemData = z.infer<typeof bulkMarkEntryItemSchema>;
