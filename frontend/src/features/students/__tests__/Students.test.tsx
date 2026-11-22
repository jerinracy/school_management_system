import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { StudentsListPage } from "@/features/students/pages/StudentsListPage";
import { StudentIDCardPreview } from "@/features/students/components/StudentIDCardPreview";
import type { StudentDetail } from "@/features/students/api/studentsApi";

const mockStudents = [
  {
    id: "stu-1",
    student_id: "2026100001",
    name_en: "Tanvir Hasan",
    name_bn: "তানভীর হাসান",
    gender: "male",
    blood_group: "B+",
    religion: "islam",
    status: "active",
    admission_date: "2026-01-05",
    active_enrollment: {
      class_name: "Class 10",
      section_name: "Section A",
      roll_no: 1,
      session_name: "2026 Academic Year",
    },
  },
  {
    id: "stu-2",
    student_id: "2026100002",
    name_en: "Nusrat Jahan",
    name_bn: "নুসরাত জাহান",
    gender: "female",
    blood_group: "O+",
    religion: "islam",
    status: "active",
    admission_date: "2026-01-06",
    active_enrollment: {
      class_name: "Class 10",
      section_name: "Section B",
      roll_no: 2,
      session_name: "2026 Academic Year",
    },
  },
];

function renderStudentsListPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

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
    permissions: ["students.view", "students.manage"],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <StudentsListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("StudentsListPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/v1/students/", () => {
        return HttpResponse.json({
          count: mockStudents.length,
          next: null,
          previous: null,
          results: mockStudents,
        });
      }),
    );
  });

  it("renders student roster and directory details correctly", async () => {
    renderStudentsListPage();

    await waitFor(() => {
      expect(screen.getByText("Tanvir Hasan")).toBeInTheDocument();
      expect(screen.getByText("2026100001")).toBeInTheDocument();
      expect(screen.getByText("Nusrat Jahan")).toBeInTheDocument();
      expect(screen.getByText("2026100002")).toBeInTheDocument();
    });

    expect(screen.getByText("Class 10 • Section A")).toBeInTheDocument();
    expect(screen.getByText("Roll 1")).toBeInTheDocument();
  });

  it("renders empty state when no students match", async () => {
    server.use(
      http.get("/api/v1/students/", () => {
        return HttpResponse.json({
          count: 0,
          next: null,
          previous: null,
          results: [],
        });
      }),
    );

    renderStudentsListPage();

    await waitFor(() => {
      expect(screen.getByText("No students found")).toBeInTheDocument();
    });
  });
});

describe("StudentIDCardPreview", () => {
  const sampleStudent: StudentDetail = {
    id: "stu-1",
    student_id: "2026100001",
    name_en: "Tanvir Hasan",
    name_bn: "তানভীর হাসান",
    dob: "2010-05-15",
    gender: "male",
    blood_group: "B+",
    religion: "islam",
    birth_reg_no: "20101234567890123",
    present_address: "Dhanmondi, Dhaka",
    permanent_address: "Dhanmondi, Dhaka",
    status: "active",
    admission_date: "2026-01-05",
    emergency_contact_name: "Rafiqul Islam",
    emergency_contact_phone: "+8801712345678",
    has_app_account: true,
    user_id: "usr-1",
    login_phone: "+8801712345678",
    enrollments: [
      {
        id: "enr-1",
        student: "stu-1",
        student_name_en: "Rahim Uddin",
        student_name_bn: "রহিম উদ্দিন",
        student_id_number: "STU-2026-00001",
        gender: "male",
        avatar_url: null,
        session: "sess-1",
        session_name: "2026 Academic Year",
        class_level: "cls-10",
        class_name: "Class 10",
        section: "sec-a",
        section_name: "Section A",
        roll_no: 1,
        group_name: "",
        shift_name: "",
        enrollment_date: "2026-01-05",
        status: "active",
      },
    ],
    documents: [],
    id_cards: [],
    guardians: [],
    previous_school: {
      id: "ps-1",
      school_name: "Dhaka Collegiate School",
    },
    created_at: "2026-01-05T00:00:00Z",
    updated_at: "2026-01-05T00:00:00Z",
  };

  it("renders student CR80 identity card with institutional details", () => {
    render(<StudentIDCardPreview student={sampleStudent} />);

    expect(screen.getByText("Student ID")).toBeInTheDocument();
    expect(screen.getByText("Tanvir Hasan")).toBeInTheDocument();
    expect(screen.getByText("Class 10")).toBeInTheDocument();
    expect(screen.getByText("B+")).toBeInTheDocument();
    expect(screen.getByText("Section A (1)")).toBeInTheDocument();
  });
});
