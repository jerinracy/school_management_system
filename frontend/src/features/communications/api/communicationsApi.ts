import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";

export type GatewayProvider = "ssl_wireless" | "greenweb" | "banglalink" | "grameenphone" | "robi" | "teletalk" | "mock_console";
export type ChannelType = "sms" | "push" | "email" | "in_app" | "all";
export type DeliveryStatus = "queued" | "sent" | "delivered" | "failed";
export type NoticeCategory = "general" | "academic" | "exam" | "fee" | "holiday" | "emergency";
export type NoticeAudience = "all" | "students" | "guardians" | "teachers" | "staff" | "specific_class";
export type EmergencySeverity = "warning" | "critical" | "disaster";

export interface SMSGatewayConfig {
  id: string;
  name: string;
  provider: GatewayProvider;
  sender_id: string;
  is_masking: boolean;
  api_key_masked: string;
  client_id?: string;
  endpoint_url?: string;
  is_active: boolean;
  is_default: boolean;
  rate_per_segment: string;
  balance: string;
  last_balance_check?: string | null;
  rate_limit_per_minute?: number;
}

export interface NotificationTemplate {
  id: string;
  name: string;
  code: string;
  channel: ChannelType;
  subject_template?: string;
  body_template_en: string;
  body_template_bn: string;
  variables_schema?: unknown;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationDelivery {
  id: string;
  recipient_name: string;
  recipient_phone: string;
  recipient_email?: string;
  channel: ChannelType;
  title: string;
  content: string;
  language: "bn" | "en";
  status: DeliveryStatus;
  provider_message_id?: string;
  error_message?: string;
  segment_count: number;
  cost_bdt: string;
  sent_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
}

export interface Notice {
  id: string;
  title_en: string;
  title_bn?: string;
  content_en: string;
  content_bn?: string;
  category: NoticeCategory;
  target_audience: NoticeAudience;
  target_class_level?: string | null;
  class_level_name?: string;
  target_section?: string | null;
  section_name?: string;
  is_pinned: boolean;
  is_published: boolean;
  publish_date?: string;
  expiry_date?: string | null;
  attachment?: string | null;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface EmergencyAlert {
  id: string;
  title: string;
  message_bn: string;
  message_en?: string;
  severity: EmergencySeverity;
  channels: ChannelType[];
  sent_by_name: string;
  sent_at: string;
  total_recipients: number;
  successful_deliveries: number;
  failed_deliveries: number;
}

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

export const communicationsApi = {
  // Gateways
  async getGateways(): Promise<PaginatedResult<SMSGatewayConfig>> {
    const res = await apiClient.GET("/api/v1/communications/gateways/", {});
    return checkResponse<PaginatedResult<SMSGatewayConfig>>(res);
  },

  async checkGatewayBalance(gatewayId: string): Promise<{ balance: string; currency: string }> {
    const res = await apiClient.POST("/api/v1/communications/gateways/{id}/check-balance/", {
      params: { path: { id: gatewayId } },
      body: {} as never,
    } as never);
    return checkResponse<{ balance: string; currency: string }>(res);
  },

  async sendTestSMS(data: { phone: string; message: string; gateway_id?: string }): Promise<NotificationDelivery> {
    const res = await apiClient.POST("/api/v1/communications/gateways/send-test/", {
      body: data as never,
    });
    return checkResponse<NotificationDelivery>(res);
  },

  // Templates
  async getTemplates(params?: { channel?: string; is_active?: boolean; search?: string }): Promise<PaginatedResult<NotificationTemplate>> {
    const res = await apiClient.GET("/api/v1/communications/templates/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<NotificationTemplate>>(res);
  },

  async previewTemplate(templateId: string, data: { variables?: Record<string, string>; language?: "bn" | "en" }): Promise<{ subject: string; body: string; language: string }> {
    const res = await apiClient.POST("/api/v1/communications/templates/{id}/preview/", {
      params: { path: { id: templateId } },
      body: data as never,
    });
    return checkResponse<{ subject: string; body: string; language: string }>(res);
  },

  async createTemplate(data: Partial<NotificationTemplate>): Promise<NotificationTemplate> {
    const res = await apiClient.POST("/api/v1/communications/templates/", {
      body: data as never,
    });
    return checkResponse<NotificationTemplate>(res);
  },

  // Deliveries
  async getDeliveries(params?: {
    channel?: string;
    status?: string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResult<NotificationDelivery>> {
    const res = await apiClient.GET("/api/v1/communications/deliveries/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<NotificationDelivery>>(res);
  },

  // Notices
  async getNotices(params?: {
    category?: string;
    target_audience?: string;
    is_pinned?: boolean;
    is_published?: boolean;
    search?: string;
  }): Promise<PaginatedResult<Notice>> {
    const res = await apiClient.GET("/api/v1/communications/notices/", {
      params: { query: params as never },
    });
    return checkResponse<PaginatedResult<Notice>>(res);
  },

  async getNoticeDetail(id: string): Promise<Notice> {
    const res = await apiClient.GET("/api/v1/communications/notices/{id}/", {
      params: { path: { id } },
    });
    return checkResponse<Notice>(res);
  },

  async createNotice(data: Partial<Notice>): Promise<Notice> {
    const res = await apiClient.POST("/api/v1/communications/notices/", {
      body: data as never,
    });
    return checkResponse<Notice>(res);
  },

  async pinNotice(id: string): Promise<{ status: string }> {
    const res = await apiClient.POST("/api/v1/communications/notices/{id}/pin/", {
      params: { path: { id } },
      body: {} as never,
    } as never);
    return checkResponse<{ status: string }>(res);
  },

  async unpinNotice(id: string): Promise<{ status: string }> {
    const res = await apiClient.POST("/api/v1/communications/notices/{id}/unpin/", {
      params: { path: { id } },
      body: {} as never,
    } as never);
    return checkResponse<{ status: string }>(res);
  },

  // Emergency Alerts
  async getEmergencyAlerts(): Promise<PaginatedResult<EmergencyAlert>> {
    const res = await apiClient.GET("/api/v1/communications/emergency-alerts/", {});
    return checkResponse<PaginatedResult<EmergencyAlert>>(res);
  },

  async broadcastEmergencyAlert(data: {
    title: string;
    message_bn: string;
    message_en?: string;
    severity: EmergencySeverity;
    channels: ChannelType[];
  }): Promise<EmergencyAlert> {
    const res = await apiClient.POST("/api/v1/communications/emergency-alerts/", {
      body: data as never,
    });
    return checkResponse<EmergencyAlert>(res);
  },
};
