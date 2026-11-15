import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";

export interface PaginatedResult<T> {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
}

function checkResponse<T>(res: { data?: unknown; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

// ---------------------------------------------------------------------------
// HOMEWORK & ASSIGNMENTS TYPES
// ---------------------------------------------------------------------------
export type HomeworkStatus = "draft" | "published" | "closed";
export type SubmissionStatus = "submitted" | "graded" | "late" | "resubmission_requested";

export interface HomeworkAssignment {
  id: string;
  session?: string;
  class_level: string;
  class_level_name?: string;
  section?: string | null;
  section_name?: string | null;
  subject: string;
  subject_name?: string;
  teacher?: string;
  teacher_name?: string;
  title: string;
  description: string;
  instructions?: string;
  assigned_at: string;
  due_at: string;
  allow_late_submission: boolean;
  late_submission_cutoff_at?: string | null;
  max_marks: number;
  status: HomeworkStatus;
  published_at?: string | null;
  attachments?: Array<{ id: string; file_name: string; file_url: string; file_size?: number }>;
  created_at: string;
  updated_at: string;
}

export interface HomeworkSubmission {
  id: string;
  homework: string;
  homework_title?: string;
  student: string;
  student_code?: string;
  student_name?: string;
  text_response?: string;
  submitted_at: string;
  is_late: boolean;
  status: SubmissionStatus;
  marks_obtained?: string | number | null;
  feedback?: string | null;
  graded_by?: string | null;
  graded_at?: string | null;
  attachments?: Array<{ id: string; file_name: string; file_url: string }>;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// LIBRARY CATALOG & CIRCULATION TYPES
// ---------------------------------------------------------------------------
export interface Book {
  id: string;
  isbn?: string;
  title: string;
  title_bn?: string;
  authors: string;
  category?: string;
  publisher?: string;
  edition?: string;
  publication_year?: number;
  language?: string;
  subject?: string;
  description?: string;
  cover_image_url?: string | null;
  is_reference_only: boolean;
  total_copies: number;
  available_copies: number;
  issue_count?: number;
  created_at: string;
  updated_at: string;
}

export type BookIssueStatus = "issued" | "returned" | "overdue" | "lost";

export interface BookIssue {
  id: string;
  copy: string;
  book_title?: string;
  accession_no?: string;
  barcode?: string;
  member: string;
  card_number?: string;
  issued_by?: string;
  returned_to?: string | null;
  issue_date: string;
  due_date: string;
  return_date?: string | null;
  renewal_count: number;
  status: BookIssueStatus;
  remarks?: string;
  created_at: string;
  updated_at: string;
}

export interface LibraryFine {
  id: string;
  issue: string;
  book_title?: string;
  member: string;
  card_number?: string;
  reason: string;
  overdue_days: number;
  amount: string;
  paid_amount: string;
  status: "pending" | "paid" | "waived";
  paid_at?: string | null;
  payment_reference?: string;
  waived_by?: string | null;
  waive_reason?: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// TRANSPORT FLEET & ROUTES TYPES
// ---------------------------------------------------------------------------
export type VehicleType = "bus" | "minibus" | "van";
export type VehicleStatus = "active" | "maintenance" | "inactive";

export interface Vehicle {
  id: string;
  registration_no: string;
  vehicle_type: VehicleType;
  capacity: number;
  make_model?: string;
  fitness_expiry?: string | null;
  insurance_expiry?: string | null;
  tax_token_expiry?: string | null;
  route_permit_expiry?: string | null;
  gps_device_id?: string | null;
  status: VehicleStatus;
  created_at: string;
  updated_at: string;
}

export interface Driver {
  id: string;
  staff: string;
  staff_name?: string;
  license_no: string;
  license_expiry?: string | null;
  helper_name?: string;
  helper_phone?: string;
  status: "active" | "on_leave" | "suspended";
  created_at: string;
  updated_at: string;
}

export interface RouteStop {
  id: string;
  route: string;
  name: string;
  order: number;
  pickup_time: string;
  drop_time: string;
  stop_fee_override?: string | null;
}

export interface TransportRoute {
  id: string;
  name: string;
  code: string;
  vehicle?: string | null;
  vehicle_registration?: string;
  driver?: string | null;
  monthly_fee: string;
  is_active: boolean;
  stops?: RouteStop[];
  created_at: string;
  updated_at: string;
}

export interface TransportAssignment {
  id: string;
  student: string;
  student_name?: string;
  route: string;
  route_name?: string;
  stop?: string;
  stop_name?: string;
  pickup_opted: boolean;
  drop_opted: boolean;
  is_active: boolean;
  effective_from: string;
  effective_until?: string | null;
}

// ---------------------------------------------------------------------------
// HOSTEL DORMS & ALLOCATIONS TYPES
// ---------------------------------------------------------------------------
export type HostelType = "boys" | "girls" | "coed" | "staff";
export type BedStatus = "available" | "occupied" | "maintenance" | "reserved";

export interface Hostel {
  id: string;
  name: string;
  code: string;
  hostel_type: HostelType;
  warden?: string | null;
  curfew_time: string;
  address?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HostelRoom {
  id: string;
  hostel: string;
  room_number: string;
  floor: number;
  capacity: number;
  monthly_fee: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Bed {
  id: string;
  room: string;
  bed_number: string;
  status: BedStatus;
  created_at: string;
  updated_at: string;
}

export interface HostelAllocation {
  id: string;
  session?: string;
  student: string;
  student_name?: string;
  hostel: string;
  hostel_name?: string;
  room: string;
  bed: string;
  allocated_date: string;
  vacated_date?: string | null;
  is_active: boolean;
  remarks?: string;
  created_at: string;
  updated_at: string;
}

export type GatePassStatus = "pending" | "approved" | "rejected" | "departed" | "returned" | "overdue";

export interface GatePass {
  id: string;
  student: string;
  student_name?: string;
  hostel: string;
  hostel_name?: string;
  reason: string;
  destination: string;
  expected_out_at: string;
  expected_return_at: string;
  actual_out_at?: string | null;
  actual_return_at?: string | null;
  guardian_confirmed_at?: string | null;
  approved_by?: string | null;
  status: GatePassStatus;
  curfew_alert_sent: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// OPERATIONS API CLIENT
// ---------------------------------------------------------------------------
export const operationsApi = {
  // 1. HOMEWORK & ASSIGNMENTS
  async getAssignments(params?: {
    class_level?: string;
    section?: string;
    subject?: string;
    status?: string;
    search?: string;
  }): Promise<PaginatedResult<HomeworkAssignment>> {
    const res = await apiClient.GET("/api/v1/homework/assignments/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<HomeworkAssignment>>(res);
  },

  async getAssignmentDetail(id: string): Promise<HomeworkAssignment> {
    const res = await apiClient.GET("/api/v1/homework/assignments/{id}/", {
      params: { path: { id } },
    });
    return checkResponse<HomeworkAssignment>(res);
  },

  async createAssignment(data: Partial<HomeworkAssignment>): Promise<HomeworkAssignment> {
    const res = await apiClient.POST("/api/v1/homework/assignments/", {
      body: data as never,
    });
    return checkResponse<HomeworkAssignment>(res);
  },

  async publishAssignment(id: string): Promise<{ status: string }> {
    const res = await apiClient.POST("/api/v1/homework/assignments/{id}/publish/", {
      params: { path: { id } },
      body: {} as never,
    } as never);
    return checkResponse<{ status: string }>(res);
  },

  async closeAssignment(id: string): Promise<{ status: string }> {
    const res = await apiClient.POST("/api/v1/homework/assignments/{id}/close/", {
      params: { path: { id } },
      body: {} as never,
    } as never);
    return checkResponse<{ status: string }>(res);
  },

  async getSubmissions(params?: {
    homework?: string;
    student?: string;
    status?: string;
  }): Promise<PaginatedResult<HomeworkSubmission>> {
    const res = await apiClient.GET("/api/v1/homework/submissions/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<HomeworkSubmission>>(res);
  },

  async gradeSubmission(
    id: string,
    data: { marks_obtained: number; feedback?: string }
  ): Promise<HomeworkSubmission> {
    const res = await apiClient.POST("/api/v1/homework/submissions/{id}/grade/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse<HomeworkSubmission>(res);
  },

  // 2. LIBRARY CATALOG & CIRCULATION
  async getBooks(params?: {
    category?: string;
    subject?: string;
    search?: string;
  }): Promise<PaginatedResult<Book>> {
    const res = await apiClient.GET("/api/v1/library/books/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<Book>>(res);
  },

  async createBook(data: Partial<Book>): Promise<Book> {
    const res = await apiClient.POST("/api/v1/library/books/", {
      body: data as never,
    });
    return checkResponse<Book>(res);
  },

  async getIssues(params?: {
    status?: string;
    member?: string;
    search?: string;
  }): Promise<PaginatedResult<BookIssue>> {
    const res = await apiClient.GET("/api/v1/library/issues/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<BookIssue>>(res);
  },

  async issueBook(data: {
    copy: string;
    member: string;
    due_date?: string;
    remarks?: string;
  }): Promise<BookIssue> {
    const res = await apiClient.POST("/api/v1/library/issues/issue/", {
      body: data as never,
    });
    return checkResponse<BookIssue>(res);
  },

  async returnBook(data: { copy: string; remarks?: string }): Promise<BookIssue> {
    const res = await apiClient.POST("/api/v1/library/issues/return/", {
      body: data as never,
    });
    return checkResponse<BookIssue>(res);
  },

  async renewBook(data: { copy: string; additional_days?: number }): Promise<BookIssue> {
    const res = await apiClient.POST("/api/v1/library/issues/renew/", {
      body: data as never,
    });
    return checkResponse<BookIssue>(res);
  },

  async getFines(params?: { status?: string }): Promise<PaginatedResult<LibraryFine>> {
    const res = await apiClient.GET("/api/v1/library/fines/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<LibraryFine>>(res);
  },

  async payFine(id: string, data: { payment_reference?: string }): Promise<LibraryFine> {
    const res = await apiClient.POST("/api/v1/library/fines/{id}/pay/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse<LibraryFine>(res);
  },

  async waiveFine(id: string, data: { waive_reason: string }): Promise<LibraryFine> {
    const res = await apiClient.POST("/api/v1/library/fines/{id}/waive/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse<LibraryFine>(res);
  },

  // 3. TRANSPORT FLEET & ROUTES
  async getVehicles(params?: { status?: string; search?: string }): Promise<PaginatedResult<Vehicle>> {
    const res = await apiClient.GET("/api/v1/transport/vehicles/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<Vehicle>>(res);
  },

  async createVehicle(data: Partial<Vehicle>): Promise<Vehicle> {
    const res = await apiClient.POST("/api/v1/transport/vehicles/", {
      body: data as never,
    });
    return checkResponse<Vehicle>(res);
  },

  async getDrivers(): Promise<PaginatedResult<Driver>> {
    const res = await apiClient.GET("/api/v1/transport/drivers/", {});
    return checkResponse<PaginatedResult<Driver>>(res);
  },

  async createDriver(data: Partial<Driver>): Promise<Driver> {
    const res = await apiClient.POST("/api/v1/transport/drivers/", {
      body: data as never,
    });
    return checkResponse<Driver>(res);
  },

  async getRoutes(): Promise<PaginatedResult<TransportRoute>> {
    const res = await apiClient.GET("/api/v1/transport/routes/", {});
    return checkResponse<PaginatedResult<TransportRoute>>(res);
  },

  async createRoute(data: Partial<TransportRoute>): Promise<TransportRoute> {
    const res = await apiClient.POST("/api/v1/transport/routes/", {
      body: data as never,
    });
    return checkResponse<TransportRoute>(res);
  },

  async getTransportAssignments(params?: { route?: string }): Promise<PaginatedResult<TransportAssignment>> {
    const res = await apiClient.GET("/api/v1/transport/assignments/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<TransportAssignment>>(res);
  },

  // 4. HOSTEL DORMS & ALLOCATIONS
  async getHostels(): Promise<PaginatedResult<Hostel>> {
    const res = await apiClient.GET("/api/v1/hostel/hostels/", {});
    return checkResponse<PaginatedResult<Hostel>>(res);
  },

  async getHostelRooms(params?: { hostel?: string }): Promise<PaginatedResult<HostelRoom>> {
    const res = await apiClient.GET("/api/v1/hostel/rooms/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<HostelRoom>>(res);
  },

  async getBeds(params?: { room?: string; status?: string }): Promise<PaginatedResult<Bed>> {
    const res = await apiClient.GET("/api/v1/hostel/beds/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<Bed>>(res);
  },

  async getHostelAllocations(params?: { hostel?: string; is_active?: boolean }): Promise<PaginatedResult<HostelAllocation>> {
    const res = await apiClient.GET("/api/v1/hostel/allocations/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<HostelAllocation>>(res);
  },

  async createHostelAllocation(data: Partial<HostelAllocation>): Promise<HostelAllocation> {
    const res = await apiClient.POST("/api/v1/hostel/allocations/", {
      body: data as never,
    });
    return checkResponse<HostelAllocation>(res);
  },

  async vacateHostelAllocation(id: string, data: { vacated_date?: string; remarks?: string }): Promise<{ status: string }> {
    const res = await apiClient.POST("/api/v1/hostel/allocations/{id}/vacate/", {
      params: { path: { id } },
      body: data as never,
    });
    return checkResponse<{ status: string }>(res);
  },

  async getGatePasses(params?: { status?: string }): Promise<PaginatedResult<GatePass>> {
    const res = await apiClient.GET("/api/v1/hostel/gate-passes/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<GatePass>>(res);
  },
};
