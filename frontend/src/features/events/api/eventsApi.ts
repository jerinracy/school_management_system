import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";

export interface UnifiedCalendarItem {
  id: string;
  source_type: "event" | "holiday" | "notice";
  category: string;
  title_en: string;
  title_bn: string;
  description: string;
  start: string;
  end: string | null;
  is_all_day: boolean;
  venue: string;
  is_pinned: boolean;
}

export interface AcademicEvent {
  id: string;
  title_en: string;
  title_bn?: string;
  description_en?: string;
  description_bn?: string;
  category: "academic" | "sports" | "annual_function" | "national_day" | "cultural" | "other";
  start_datetime: string;
  end_datetime: string;
  is_all_day: boolean;
  venue?: string;
  target_audience: "all" | "students" | "guardians" | "teachers" | "staff" | "specific_class";
  is_published: boolean;
  created_at: string;
}

function checkResponse<T>(res: { data?: unknown; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

export const eventsApi = {
  async getUnifiedCalendar(params?: { start_date?: string; end_date?: string }): Promise<UnifiedCalendarItem[]> {
    const res = await apiClient.GET("/api/v1/events/calendar/", {
      params: { query: params as never },
    });
    return checkResponse<UnifiedCalendarItem[]>(res);
  },

  async createEvent(data: Partial<AcademicEvent>): Promise<AcademicEvent> {
    const res = await apiClient.POST("/api/v1/events/events/", {
      body: data as never,
    });
    return checkResponse<AcademicEvent>(res);
  },
};
