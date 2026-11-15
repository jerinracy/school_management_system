import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";
import type { paths } from "@/types/api";

export type ExamResultItem = paths["/api/v1/results/exam-results/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type SubjectResultItem = paths["/api/v1/results/subject-results/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type TabulationSheetItem = paths["/api/v1/results/tabulation-sheets/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type ReportCardItem = paths["/api/v1/results/report-cards/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];
export type GradingScaleItem = paths["/api/v1/results/grading-scales/"]["get"]["responses"]["200"]["content"]["application/json"]["results"][number];

function checkResponse<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

export const resultsApi = {
  // Calculation & Results
  async calculateExamResults(examId: string, asyncMode = false) {
    const res = await apiClient.POST("/api/v1/results/exam-results/calculate/", {
      body: { exam_id: examId, async_mode: asyncMode } as never,
    });
    return checkResponse(res);
  },

  async getExamResults(params?: {
    exam?: string;
    class_level?: string;
    section?: string;
    is_passed?: boolean;
    search?: string;
    page?: number;
  }) {
    const res = await apiClient.GET("/api/v1/results/exam-results/", {
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

  async getExamResultSummary(examId: string) {
    const res = await apiClient.GET("/api/v1/results/exam-results/summary/", {
      params: {
        query: { exam_id: examId } as never,
      },
    });
    return checkResponse(res);
  },

  // Subject Results
  async getSubjectResults(params?: { exam?: string; exam_subject?: string; student?: string }) {
    const res = await apiClient.GET("/api/v1/results/subject-results/", {
      params: {
        query: {
          exam: params?.exam,
          exam_subject: params?.exam_subject,
          student: params?.student,
        },
      },
    });
    return checkResponse(res);
  },

  // Tabulation Sheets
  async getTabulationSheets(params?: { exam?: string; class_level?: string }) {
    const res = await apiClient.GET("/api/v1/results/tabulation-sheets/", {
      params: {
        query: {
          exam: params?.exam,
          class_level: params?.class_level,
        },
      },
    });
    return checkResponse(res);
  },

  async createTabulationSheet(payload: { exam: string; class_level: string; section?: string; file_format?: "pdf" | "excel" | "csv" }) {
    const res = await apiClient.POST("/api/v1/results/tabulation-sheets/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  // Report Cards
  async getReportCards(params?: { exam?: string; student?: string; page?: number }) {
    const res = await apiClient.GET("/api/v1/results/report-cards/", {
      params: {
        query: {
          exam: params?.exam,
          student: params?.student,
          page: params?.page,
        },
      },
    });
    return checkResponse(res);
  },

  async generateReportCard(examResultId: string, templateStyle = "default_bd") {
    const res = await apiClient.POST("/api/v1/results/report-cards/generate/", {
      body: { exam_result_id: examResultId, template_style: templateStyle } as never,
    });
    return checkResponse(res);
  },

  async bulkZipReportCards(payload: { exam_id: string; class_level_id: string; section_id?: string }) {
    const res = await apiClient.POST("/api/v1/results/report-cards/bulk_zip/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  // Publication & Approvals
  async approveResults(examId: string, remarks?: string) {
    const res = await apiClient.POST("/api/v1/results/publications/approve/", {
      body: { exam_id: examId, remarks } as never,
    });
    return checkResponse(res);
  },

  async publishResults(payload: {
    exam_id: string;
    is_visible_to_guardians?: boolean;
    is_visible_to_students?: boolean;
    allow_public_search?: boolean;
    remarks?: string;
  }) {
    const res = await apiClient.POST("/api/v1/results/publications/publish/", {
      body: payload as never,
    });
    return checkResponse(res);
  },

  async unpublishResults(examId: string) {
    const res = await apiClient.POST("/api/v1/results/publications/unpublish/", {
      body: { exam_id: examId } as never,
    });
    return checkResponse(res);
  },

  // Grading Scales
  async getGradingScales() {
    const res = await apiClient.GET("/api/v1/results/grading-scales/");
    return checkResponse(res).results ?? [];
  },

  async seedBdDefaults() {
    const res = await apiClient.POST("/api/v1/results/grading-scales/seed_bd_defaults/", {
      body: {} as never,
    });
    return checkResponse(res);
  },
};
