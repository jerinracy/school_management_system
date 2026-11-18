import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths } from "@/types/api";

export type ExamItem = paths["/api/v1/exams/exams/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type ExamTypeItem = paths["/api/v1/exams/types/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type ExamSubjectItem = paths["/api/v1/exams/subjects/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type ExamRoutineItem = paths["/api/v1/exams/routines/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type MarkEntryItem = paths["/api/v1/exams/mark-entries/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type AdmitCardItem = paths["/api/v1/exams/admit-cards/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type EligibilityItem = paths["/api/v1/exams/eligibilities/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];

function checkResponse<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

function checkVoid(res: { error?: unknown; response: Response }): void {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
}

export const examsApi = {
  // Exams
  async getExams(params?: { session?: string; status?: string; search?: string; page?: number }) {
    const query: Record<string, string | number> = {};
    if (params?.session) query.session = params.session;
    if (params?.status) query.status = params.status;
    if (params?.search) query.search = params.search;
    if (params?.page) query.page = params.page;

    const res = await apiClient.GET("/api/v1/exams/exams/", {
      params: Object.keys(query).length > 0 ? { query: query as never } : undefined,
    });
    return checkResponse(res);
  },

  async getExam(id: string) {
    const res = await apiClient.GET("/api/v1/exams/exams/{id}/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  async createExam(payload: {
    name: string;
    exam_type: string;
    session: string;
    start_date: string;
    end_date: string;
    term?: string;
    weightage?: string;
    target_classes?: string[];
  }) {
    const res = await apiClient.POST("/api/v1/exams/exams/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async updateExam(id: string, payload: Partial<ExamItem>) {
    const res = await apiClient.PATCH("/api/v1/exams/exams/{id}/", {
      params: { path: { id } },
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteExam(id: string) {
    const res = await apiClient.DELETE("/api/v1/exams/exams/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  async getExamProgress(id: string) {
    const res = await apiClient.GET("/api/v1/exams/exams/{id}/progress/", {
      params: { path: { id } },
    });
    return checkResponse(res);
  },

  // Exam Types
  async getExamTypes() {
    const res = await apiClient.GET("/api/v1/exams/types/");
    return checkResponse(res).results ?? [];
  },

  async createExamType(payload: {
    name: string;
    code: string;
    is_board_exam?: boolean;
    description?: string;
  }) {
    const res = await apiClient.POST("/api/v1/exams/types/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async updateExamType(
    id: string,
    payload: Partial<{
      name: string;
      code: string;
      is_board_exam?: boolean;
      description?: string;
    }>,
  ) {
    const res = await apiClient.PATCH("/api/v1/exams/types/{id}/", {
      params: { path: { id } },
      body: payload as never,
    });
    return checkResponse(res);
  },

  async deleteExamType(id: string) {
    const res = await apiClient.DELETE("/api/v1/exams/types/{id}/", {
      params: { path: { id } },
    });
    checkVoid(res);
  },

  // Exam Subjects
  async getExamSubjects(params?: { exam?: string; class_level?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/exams/subjects/", {
      params: {
        query: {
          exam: params?.exam,
          class_level: params?.class_level,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async createExamSubject(payload: {
    exam: string;
    class_level: string;
    subject: string;
    exam_date?: string | null;
    start_time?: string | null;
    end_time?: string | null;
    full_marks?: string;
    pass_marks?: string;
    creative_full_marks?: string;
    creative_pass_marks?: string;
    mcq_full_marks?: string;
    mcq_pass_marks?: string;
    practical_full_marks?: string;
    practical_pass_marks?: string;
    is_combined_paper?: boolean;
    combined_with?: string | null;
    assigned_teacher?: string | null;
  }) {
    const res = await apiClient.POST("/api/v1/exams/subjects/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  // Mark Entries
  async getMarkEntries(params?: {
    exam_subject?: string;
    student?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/exams/mark-entries/", {
      params: {
        query: {
          exam_subject: params?.exam_subject,
          student: params?.student,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async bulkSaveMarks(payload: {
    exam_subject_id: string;
    entries: Array<{
      student_id: string;
      creative_marks?: number | null;
      mcq_marks?: number | null;
      practical_marks?: number | null;
      is_absent?: boolean;
      reason?: string;
    }>;
  }) {
    const res = await apiClient.POST("/api/v1/exams/mark-entries/bulk_save/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async lockMarks(examSubjectId: string) {
    const res = await apiClient.POST("/api/v1/exams/mark-entries/lock/", {
      body: { exam_subject_id: examSubjectId } as never,
    });
    return checkResponse(res);
  },

  async unlockMarks(examSubjectId: string, reason: string) {
    const res = await apiClient.POST("/api/v1/exams/mark-entries/unlock/", {
      body: { exam_subject_id: examSubjectId, reason } as never,
    });
    return checkResponse(res);
  },

  // Routines / Timetables
  async getRoutines(params?: { exam?: string; class_level?: string }) {
    const res = await apiClient.GET("/api/v1/exams/routines/", {
      params: {
        query: {
          exam: params?.exam,
          class_level: params?.class_level,
        },
      },
    });
    return checkResponse(res);
  },

  // Eligibilities & Admit Cards
  async getEligibilities(params?: { exam?: string; is_eligible?: boolean; page?: number }) {
    const res = await apiClient.GET("/api/v1/exams/eligibilities/", {
      params: {
        query: {
          exam: params?.exam,
          is_eligible: params?.is_eligible,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async generateEligibility(examId: string) {
    const res = await apiClient.POST("/api/v1/exams/exams/{id}/generate_eligibility/", {
      params: { path: { id: examId } },
      body: {} as never,
    });
    return checkResponse(res);
  },

  async getAdmitCards(params?: { exam?: string; search?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/exams/admit-cards/", {
      params: {
        query: {
          exam: params?.exam,
          search: params?.search,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async generateAdmitCards(examId: string) {
    const res = await apiClient.POST("/api/v1/exams/exams/{id}/generate_admit_cards/", {
      params: { path: { id: examId } },
      body: {} as never,
    });
    return checkResponse(res);
  },
};
