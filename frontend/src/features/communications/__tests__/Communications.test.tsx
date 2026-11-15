import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { SMSCampaignPage } from "../pages/SMSCampaignPage";
import { NoticeBoardPage } from "../pages/NoticeBoardPage";
import { TemplatesPage } from "../pages/TemplatesPage";
import { EmergencyAlertsPage } from "../pages/EmergencyAlertsPage";
import { UnifiedCalendarPage } from "@/features/events/pages/UnifiedCalendarPage";

const mockGateways = [
  {
    id: "gw-1",
    name: "SSL Wireless Primary",
    provider: "ssl_wireless",
    sender_id: "SCHOOLDHAKA",
    is_masking: true,
    api_key_masked: "ssl_sec_****1234",
    is_active: true,
    is_default: true,
    rate_per_segment: "0.45",
    balance: "12500.00",
    last_balance_check: "2026-11-15T09:00:00Z",
  },
];

const mockNotices = [
  {
    id: "notice-1",
    title_en: "Annual Sports Day 2026",
    title_bn: "বার্ষিক ক্রীড়া প্রতিযোগিতা ২০২৬",
    content_en: "All students are requested to be present by 8:30 AM in full sports uniform.",
    content_bn: "সকল শিক্ষার্থীদের সকাল ৮:৩০ এর মধ্যে নির্ধারিত পোশাকে উপস্থিত থাকার জন্য অনুরোধ করা হচ্ছে।",
    category: "academic",
    target_audience: "all",
    is_pinned: true,
    is_published: true,
    publish_date: "2026-11-15",
    created_at: "2026-11-15T06:00:00Z",
    updated_at: "2026-11-15T06:00:00Z",
  },
  {
    id: "notice-2",
    title_en: "Admit Card Distribution for Final Term",
    title_bn: "বার্ষিক পরীক্ষার প্রবেশপত্র বিতরণ",
    content_en: "Admit cards will be distributed from class teachers upon clearance of tuition fees.",
    content_bn: "টিউশন ফি পরিশোধ সাপেক্ষে শ্রেণি শিক্ষকের নিকট হতে প্রবেশপত্র সংগ্রহ করতে হবে।",
    category: "exam",
    target_audience: "students",
    is_pinned: false,
    is_published: true,
    publish_date: "2026-11-14",
    created_at: "2026-11-14T06:00:00Z",
    updated_at: "2026-11-14T06:00:00Z",
  },
];

const mockTemplates = [
  {
    id: "tpl-1",
    name: "Tuition Fee Due Reminder",
    code: "FEE_DUE_REMINDER",
    channel: "sms",
    subject_template: "Fee Reminder",
    body_template_en: "Dear Guardian, {{student_name}}'s tuition fee of {{due_amount}} is pending.",
    body_template_bn: "প্রিয় অভিভাবক, আপনার সন্তান {{student_name}} এর মাসিক ফি {{due_amount}} টাকা বকেয়া রয়েছে।",
    is_active: true,
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-15T00:00:00Z",
  },
];

const mockEmergencyAlerts = [
  {
    id: "alert-1",
    title: "Cyclone Alert - School Closed",
    message_bn: "ঘূর্ণিঝড় সতর্কতার কারণে অদ্য বিদ্যালয়ের সকল কার্যক্রম স্থগিত থাকবে।",
    message_en: "Due to severe cyclone warning, school remains closed today.",
    severity: "critical",
    channels: ["sms", "push"],
    sent_by_name: "Principal Office",
    sent_at: "2026-11-15T05:30:00Z",
    total_recipients: 1250,
    successful_deliveries: 1242,
    failed_deliveries: 8,
  },
];

const mockCalendarItems = [
  {
    id: "cal-1",
    source_type: "event",
    category: "academic",
    title_en: "Science Fair 2026",
    title_bn: "বিজ্ঞান মেলা ২০২৬",
    description: "Annual project showcase",
    start: "2026-11-18T09:00:00Z",
    end: "2026-11-18T17:00:00Z",
    is_all_day: false,
    venue: "Main Auditorium",
    is_pinned: true,
  },
  {
    id: "cal-2",
    source_type: "holiday",
    category: "holiday",
    title_en: "National Day Off",
    title_bn: "জাতীয় ছুটির দিন",
    description: "Campus closed",
    start: "2026-11-20T00:00:00Z",
    end: "2026-11-20T23:59:59Z",
    is_all_day: true,
    venue: "",
    is_pinned: false,
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Task F12 - Communications & Notice Board Dashboard", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: "usr-admin",
        username: "admin",
        email: "admin@school.edu.bd",
        phone: "+8801700000000",
        user_type: "admin",
        institution_id: "inst-1",
        roles: ["admin"],
        permissions: ["communications.view", "communications.manage", "events.view"],
        full_name: "System Administrator",
      },
      accessToken: "access-token",
      refreshToken: "refresh-token",
      isAuthenticated: true,
    });

    server.use(
      http.get("*/api/v1/communications/gateways/", () => {
        return HttpResponse.json({
          count: mockGateways.length,
          results: mockGateways,
        });
      }),
      http.get("*/api/v1/academics/classes/", () => {
        return HttpResponse.json({
          count: 0,
          results: [],
        });
      }),
      http.get("*/api/v1/communications/notices/", () => {
        return HttpResponse.json({
          count: mockNotices.length,
          results: mockNotices,
        });
      }),
      http.get("*/api/v1/communications/templates/", () => {
        return HttpResponse.json({
          count: mockTemplates.length,
          results: mockTemplates,
        });
      }),
      http.get("*/api/v1/communications/emergency-alerts/", () => {
        return HttpResponse.json({
          count: mockEmergencyAlerts.length,
          results: mockEmergencyAlerts,
        });
      }),
      http.get("*/api/v1/events/calendar/", () => {
        return HttpResponse.json(mockCalendarItems);
      })
    );
  });

  it("renders SMS campaign composer with gateway balance and character counter", async () => {
    const { container } = renderWithClient(<SMSCampaignPage />);

    const gateways = await screen.findAllByText(/SSL Wireless Primary/i);
    expect(gateways.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/12,500.00/i)).toBeInTheDocument();

    const textarea = container.querySelector("textarea")!;
    expect(textarea).toBeInTheDocument();

    // Type English text -> GSM 7-bit segment calculator
    fireEvent.change(textarea, { target: { value: "Hello Parents, school will be closed tomorrow." } });
    expect(screen.getByText(/English GSM 7-Bit/i)).toBeInTheDocument();

    // Type Bangla text -> Unicode segment calculator
    fireEvent.change(textarea, { target: { value: "সম্মানিত অভিভাবক, আগামীকাল বিদ্যালয় বন্ধ থাকিবে।" } });
    expect(screen.getByText(/Bangla Unicode/i)).toBeInTheDocument();
  });

  it("renders Notice Board with category filtering and pinned circular highlight", async () => {
    renderWithClient(<NoticeBoardPage />);

    expect(await screen.findByText(/Annual Sports Day 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/Admit Card Distribution for Final Term/i)).toBeInTheDocument();

    // Check pinned indicator
    expect(screen.getByText("PINNED")).toBeInTheDocument();
  });

  it("renders Notification Templates with code tags and live preview", async () => {
    renderWithClient(<TemplatesPage />);

    expect(await screen.findByText(/Tuition Fee Due Reminder/i)).toBeInTheDocument();
    expect(screen.getByText(/FEE_DUE_REMINDER/i)).toBeInTheDocument();

    // Open live preview modal
    const previewBtn = screen.getByRole("button", { name: /live preview/i });
    fireEvent.click(previewBtn);

    expect(await screen.findByText(/Sample Placeholder Values:/i)).toBeInTheDocument();
    expect(screen.getByText(/রাহিম ইসলাম/i)).toBeInTheDocument();
  });

  it("renders Emergency Broadcasts with protocol warnings and confirmation safety check", async () => {
    renderWithClient(<EmergencyAlertsPage />);

    expect(await screen.findByText(/Cyclone Alert - School Closed/i)).toBeInTheDocument();
    expect(screen.getByText(/CRITICAL \/ অতি জরুরি/i)).toBeInTheDocument();
    expect(screen.getByText(/1242/i)).toBeInTheDocument(); // Delivered count

    // Open emergency broadcast dialog
    const broadcastBtn = screen.getByRole("button", { name: /broadcast emergency alert/i });
    fireEvent.click(broadcastBtn);

    expect(await screen.findByText(/Initiate Campus Emergency Broadcast/i)).toBeInTheDocument();
    const submitBtn = screen.getByRole("button", { name: /broadcast alert now/i });
    expect(submitBtn).toBeDisabled(); // Disabled until risk confirmation check

    // Check confirmation checkbox
    const confirmCheck = screen.getByRole("checkbox");
    fireEvent.click(confirmCheck);
    expect(submitBtn).not.toBeDisabled();
  });

  it("renders Unified Academic Calendar with events, holidays, and day cells", async () => {
    renderWithClient(<UnifiedCalendarPage />);

    expect(await screen.findByText(/Unified Academic Calendar/i)).toBeInTheDocument();
    expect(screen.getByText(/November 2026/i)).toBeInTheDocument();

    // Should find the mock calendar items on the page
    expect(await screen.findByTitle(/Science Fair 2026/i)).toBeInTheDocument();
  });
});
