import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import ResultsDashboardPage from "@/features/results/pages/ResultsDashboardPage";
import { ReportCardPreview } from "@/features/results/components/ReportCardPreview";

const mockExamResults = [
  {
    id: "res-1",
    exam: "exam-1",
    student: "stud-1",
    student_name: "Tanvir Ahmed",
    student_code: "STD-2026-001",
    roll_no: 1,
    class_level: "class-10",
    class_level_name: "Class 10",
    section: "sec-a",
    section_name: "Section A",
    total_marks: "845.00",
    total_full_marks: "1000.00",
    percentage: "84.50",
    gpa_without_fourth: "5.00",
    fourth_subject_bonus: "1.00",
    final_gpa: "5.00",
    final_grade: "A+",
    is_passed: true,
    failed_subject_count: 0,
    section_position: 1,
    class_position: 1,
    status: "approved" as const,
    failed_subjects_summary: [],
    calculated_at: "2026-11-15T09:00:00Z",
  },
  {
    id: "res-2",
    exam: "exam-1",
    student: "stud-2",
    student_name: "Sadia Rahman",
    student_code: "STD-2026-002",
    roll_no: 2,
    class_level: "class-10",
    class_level_name: "Class 10",
    section: "sec-a",
    section_name: "Section A",
    total_marks: "720.00",
    total_full_marks: "1000.00",
    percentage: "72.00",
    gpa_without_fourth: "4.00",
    fourth_subject_bonus: "0.50",
    final_gpa: "4.50",
    final_grade: "A",
    is_passed: true,
    failed_subject_count: 0,
    section_position: 2,
    class_position: 2,
    status: "approved" as const,
    failed_subjects_summary: [],
    calculated_at: "2026-11-15T09:00:00Z",
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
    permissions: ["results.view", "results.manage", "exams.view"],
  });
}

describe("Results & Grading Engine Tests", () => {
  beforeEach(() => {
    setupAuth();
    server.use(
      http.get("/api/v1/exams/exams/", () => {
        return HttpResponse.json({
          results: [{ id: "exam-1", name: "Annual Examination 2026", session_name: "2026", status: "tabulated" }],
        });
      }),
      http.get("/api/v1/results/exam-results/", () => {
        return HttpResponse.json({
          results: mockExamResults,
        });
      }),
      http.get("/api/v1/results/exam-results/summary/", () => {
        return HttpResponse.json({
          total_students: 2,
          passed_count: 2,
          failed_count: 0,
          pass_percentage: 100,
          average_gpa: 4.75,
          grade_distribution: {
            "A+": 1,
            A: 1,
            "A-": 0,
            B: 0,
            C: 0,
            D: 0,
            F: 0,
          },
        });
      })
    );
  });

  it("renders Results Dashboard with GPA 5.0 summary and candidate rankings", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/results?exam=exam-1"]}>
          <ResultsDashboardPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText(/Examination Results & GPA 5.0 Processing/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Tanvir Ahmed")).toBeInTheDocument();
      expect(screen.getByText("Sadia Rahman")).toBeInTheDocument();
      expect(screen.getByText("100%")).toBeInTheDocument();
      expect(screen.getByText(/Pass Rate/i)).toBeInTheDocument();
    });
  });

  it("renders official printable Report Card preview with NCTB GPA legend", () => {
    render(
      <ReportCardPreview
        result={mockExamResults[0]!}
        subjectResults={[
          {
            id: "sub-res-1",
            exam: "exam-1",
            exam_subject: "sub-1",
            subject_name: "Bangla 1st Paper",
            subject_code: "101",
            student: "stud-1",
            student_name: "Tanvir Ahmed",
            student_code: "STD-2026-001",
            full_marks: "100.00",
            creative_marks: "58.00",
            mcq_marks: "28.00",
            practical_marks: null,
            total_marks: "86.00",
            marks_percentage: "86.00",
            letter_grade: "A+",
            grade_point: "5.00",
            grace_marks: "0.00",
            is_passed: true,
            is_absent: false,
            is_fourth_subject: false,
            fail_reason: "",
          },
        ]}
      />
    );

    expect(screen.getAllByText(/Academic Progress Report/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Tanvir Ahmed")).toBeInTheDocument();
    expect(screen.getByText("Bangla 1st Paper")).toBeInTheDocument();
    expect(screen.getByText(/Final CGPA:/i)).toBeInTheDocument();
    expect(screen.getByText("5.00 / 5.00")).toBeInTheDocument();
  });
});
