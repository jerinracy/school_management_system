import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import ExamListPage from "@/features/exams/pages/ExamListPage";
import { calculateBdGrade } from "@/features/exams/pages/MarkEntryPage";

const mockExams = [
  {
    id: "exam-1",
    name: "Annual Examination 2026",
    exam_type: "type-1",
    exam_type_name: "Annual Examination",
    session: "sess-1",
    session_name: "Academic Year 2026",
    term: "Final Term",
    start_date: "2026-11-15",
    end_date: "2026-11-30",
    status: "scheduled",
    exam_subjects_count: 8,
    is_active: true,
  },
  {
    id: "exam-2",
    name: "Half-Yearly Examination 2026",
    exam_type: "type-2",
    exam_type_name: "Half-Yearly Examination",
    session: "sess-1",
    session_name: "Academic Year 2026",
    term: "Half-Yearly",
    start_date: "2026-06-01",
    end_date: "2026-06-15",
    status: "published",
    exam_subjects_count: 8,
    is_active: true,
  },
];

function setupAuth() {
  useAuthStore.getState().setTokens("acc", "ref");
  useAuthStore.getState().setUser({
    id: "user-admin",
    username: "principal",
    full_name: "School Principal",
    phone: "+8801700000000",
    email: "principal@example.com",
    user_type: "super_admin",
    institution_id: "inst-1",
    roles: ["SuperAdmin"],
    permissions: ["exams.view", "exams.manage"],
  });
}

describe("Exams Module Tests", () => {
  beforeEach(() => {
    setupAuth();
    server.use(
      http.get("/api/v1/exams/exams/", () => {
        return HttpResponse.json({
          count: 2,
          next: null,
          previous: null,
          results: mockExams,
        });
      }),
      http.get("/api/v1/exams/types/", () => {
        return HttpResponse.json({
          results: [
            { id: "type-1", name: "Annual Examination" },
            { id: "type-2", name: "Half-Yearly Examination" },
          ],
        });
      }),
      http.get("/api/v1/institutions/sessions/", () => {
        return HttpResponse.json({
          results: [{ id: "sess-1", name: "Academic Year 2026" }],
        });
      }),
      http.get("/api/v1/academics/classes/", () => {
        return HttpResponse.json({
          results: [{ id: "cls-1", name: "Class 10" }],
        });
      })
    );
  });

  it("renders examinations roster with status and metadata", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ExamListPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText(/Examinations & Continuous Assessment/i)).toBeInTheDocument();

    await waitFor(() => {
      const state = queryClient.getQueryState(["exams-list", "ALL", "ALL", ""]);
      if (state?.error) {
        throw new Error("QUERY_ERROR: " + state.error.message);
      }
      expect(state?.data).toBeDefined();
    });

    await waitFor(() => {
      expect(screen.getByText("Annual Examination 2026")).toBeInTheDocument();
      expect(screen.getByText("Half-Yearly Examination 2026")).toBeInTheDocument();
    });
  });

  it("calculates Bangladesh NCTB grading rule correctly", () => {
    // 85% total -> A+ (5.00)
    const resultAPlus = calculateBdGrade(85, 100, 58, 23, 27, 10, false);
    expect(resultAPlus.grade).toBe("A+");
    expect(resultAPlus.gp).toBe(5.0);
    expect(resultAPlus.isPassed).toBe(true);

    // Failing CQ even if total is high (> 33%)
    const failCQ = calculateBdGrade(45, 100, 15, 23, 30, 10, false);
    expect(failCQ.grade).toBe("F");
    expect(failCQ.gp).toBe(0.0);
    expect(failCQ.isPassed).toBe(false);
    expect(failCQ.reason).toBe("Failed in CQ");

    // Absent candidate
    const absent = calculateBdGrade(0, 100, 0, 23, 0, 10, true);
    expect(absent.grade).toBe("ABS");
    expect(absent.isPassed).toBe(false);
  });
});
