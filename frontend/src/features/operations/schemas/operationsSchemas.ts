import { z } from "zod";

// 1. HOMEWORK & ASSIGNMENTS
export const homeworkAssignmentSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(200),
  description: z.string().min(5, "Description must be at least 5 characters"),
  instructions: z.string().optional(),
  class_level: z.string().min(1, "Class is required"),
  section: z.string().nullable().optional(),
  subject: z.string().min(1, "Subject is required"),
  due_at: z.string().min(1, "Submission deadline is required"),
  max_marks: z.coerce.number().min(1, "Max marks must be greater than 0").max(1000),
  allow_late_submission: z.boolean(),
});

export type HomeworkAssignmentFormData = z.infer<typeof homeworkAssignmentSchema>;

export const gradeSubmissionSchema = z.object({
  marks_obtained: z.coerce.number().min(0, "Marks cannot be negative"),
  feedback: z.string().optional(),
});

export type GradeSubmissionFormData = z.infer<typeof gradeSubmissionSchema>;

// 2. LIBRARY CATALOG & CIRCULATION
export const bookSchema = z.object({
  title: z.string().min(2, "Book title is required").max(255),
  title_bn: z.string().max(255).optional(),
  authors: z.string().min(2, "Author name(s) is required").max(255),
  isbn: z.string().max(50).optional(),
  category: z.string().optional(),
  publisher: z.string().optional(),
  edition: z.string().optional(),
  publication_year: z.coerce.number().min(1900).max(2100).optional(),
  is_reference_only: z.boolean(),
});

export type BookFormData = z.infer<typeof bookSchema>;

export const issueBookSchema = z.object({
  copy: z.string().min(1, "Book accession / copy ID is required"),
  member: z.string().min(1, "Library member is required"),
  due_date: z.string().min(1, "Due date is required"),
  remarks: z.string().optional(),
});

export type IssueBookFormData = z.infer<typeof issueBookSchema>;

// 3. TRANSPORT FLEET & ROUTES
export const vehicleSchema = z.object({
  registration_no: z.string().min(3, "Registration number is required").max(50),
  vehicle_type: z.enum(["bus", "minibus", "van"]),
  capacity: z.coerce.number().min(1, "Capacity must be at least 1 seat").max(150),
  make_model: z.string().optional(),
  fitness_expiry: z.string().optional(),
  tax_token_expiry: z.string().optional(),
  status: z.enum(["active", "maintenance", "inactive"]),
});

export type VehicleFormData = z.infer<typeof vehicleSchema>;

export const transportRouteSchema = z.object({
  name: z.string().min(2, "Route name is required").max(100),
  code: z.string().min(1, "Route code is required").max(20),
  vehicle: z.string().nullable().optional(),
  driver: z.string().nullable().optional(),
  monthly_fee: z.string().min(1, "Monthly transport fare in BDT is required"),
  is_active: z.boolean(),
});

export type TransportRouteFormData = z.infer<typeof transportRouteSchema>;

// 4. HOSTEL DORMS & ALLOCATIONS
export const hostelAllocationSchema = z.object({
  student: z.string().min(1, "Student is required"),
  hostel: z.string().min(1, "Hostel building is required"),
  room: z.string().min(1, "Room is required"),
  bed: z.string().min(1, "Bed is required"),
  allocated_date: z.string().min(1, "Allocation start date is required"),
  remarks: z.string().optional(),
});

export type HostelAllocationFormData = z.infer<typeof hostelAllocationSchema>;

export const gatePassSchema = z.object({
  student: z.string().min(1, "Student is required"),
  hostel: z.string().min(1, "Hostel is required"),
  reason: z.string().min(3, "Reason for gate pass is required"),
  destination: z.string().min(2, "Destination is required"),
  expected_out_at: z.string().min(1, "Departure time is required"),
  expected_return_at: z.string().min(1, "Expected return time is required"),
});

export type GatePassFormData = z.infer<typeof gatePassSchema>;
