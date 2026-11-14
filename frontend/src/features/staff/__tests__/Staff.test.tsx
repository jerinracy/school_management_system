import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { StaffListPage } from "@/features/staff/pages/StaffListPage";
import { StaffIDCardPreview } from "@/features/staff/components/StaffIDCardPreview";
import type { StaffDetail } from "@/features/staff/api/staffApi";

const mockStaffMembers = [
  {
    id: "staff-1",
    employee_id: "EMP-2026-001",
    full_name_en: "Md. Rafiqul Islam",
    full_name_bn: "মো. রফিকুল ইসলাম",
    department: "dept-1",
    department_name: "Department of Science",
    designation: "desig-1",
    designation_title: "Senior Teacher",
    staff_type: "teacher",
    status: "active",
    phone: "+8801712345678",
    email: "rafiq@example.com",
    nid: "19851234567890123",
    joining_date: "2020-01-15",
    is_mpo: true,
    mpo_index_number: "MPO-987654",
    photo: null,
  },
  {
    id: "staff-2",
    employee_id: "EMP-2026-002",
    full_name_en: "Shamima Akhter",
    full_name_bn: "শামীমা আক্তার",
    department: "dept-2",
    department_name: "Administration",
    designation: "desig-2",
    designation_title: "Accountant",
    staff_type: "admin",
    status: "active",
    phone: "+8801812345678",
    email: "shamima@example.com",
    nid: "19901234567890123",
    joining_date: "2021-03-01",
    is_mpo: false,
    mpo_index_number: null,
    photo: null,
  },
];

function renderStaffListPage() {
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
    permissions: ["staff.view", "staff.manage"],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <StaffListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("StaffListPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/v1/staff/departments/", () => {
        return HttpResponse.json({
          count: 2,
          next: null,
          previous: null,
          results: [
            { id: "dept-1", name: "Department of Science", code: "SCI" },
            { id: "dept-2", name: "Administration", code: "ADMIN" },
          ],
        });
      }),
      http.get("/api/v1/staff/staff/", () => {
        return HttpResponse.json({
          count: mockStaffMembers.length,
          next: null,
          previous: null,
          results: mockStaffMembers,
        });
      }),
    );
  });

  it("renders employee directory with correct staff details and MPO status", async () => {
    renderStaffListPage();

    await waitFor(() => {
      expect(screen.getByText("Md. Rafiqul Islam")).toBeInTheDocument();
      expect(screen.getByText("EMP-2026-001")).toBeInTheDocument();
      expect(screen.getByText("Shamima Akhter")).toBeInTheDocument();
      expect(screen.getByText("EMP-2026-002")).toBeInTheDocument();
    });

    expect(screen.getByText("Senior Teacher")).toBeInTheDocument();
    expect(screen.getByText("Accountant")).toBeInTheDocument();
    expect(screen.getByText("MPO")).toBeInTheDocument();
  });

  it("renders empty state when no staff match", async () => {
    server.use(
      http.get("/api/v1/staff/staff/", () => {
        return HttpResponse.json({
          count: 0,
          next: null,
          previous: null,
          results: [],
        });
      }),
    );

    renderStaffListPage();

    await waitFor(() => {
      expect(screen.getByText("No staff records match your criteria.")).toBeInTheDocument();
    });
  });
});

describe("StaffIDCardPreview", () => {
  const sampleStaff: StaffDetail = {
    id: "staff-1",
    employee_id: "EMP-2026-001",
    full_name_en: "Md. Rafiqul Islam",
    full_name_bn: "মো. রফিকুল ইসলাম",
    gender: "male",
    dob: "1985-05-12",
    blood_group: "B+",
    phone: "+8801712345678",
    alt_phone: "",
    email: "rafiq@example.com",
    nid: "19851234567890123",
    present_address: "Dhanmondi, Dhaka",
    permanent_address: "Comilla",
    photo: null,
    joining_date: "2020-01-15",
    confirmation_date: "2021-01-15",
    department: "dept-1",
    designation: "desig-1",
    staff_type: "teacher",
    status: "active",
    is_mpo: true,
    mpo_index_number: "MPO-987654",
    tin_number: "123456789012",
    emergency_contact_name: "Mrs. Islam",
    emergency_contact_phone: "+8801799999999",
    emergency_contact_relation: "spouse",
    department_name: "Department of Science",
    designation_title: "Senior Teacher",
    educations: [],
    documents: [],
    id_cards: [],
  };

  it("renders CR80 ID card with name, designation, blood group, and ID", () => {
    render(<StaffIDCardPreview staff={sampleStaff} />);

    expect(screen.getByText("Md. Rafiqul Islam")).toBeInTheDocument();
    expect(screen.getByText(/EMP-2026-001/)).toBeInTheDocument();
    expect(screen.getByText("Senior Teacher")).toBeInTheDocument();
    expect(screen.getByText("B+")).toBeInTheDocument();
    expect(screen.getByText(/\+8801712345678/)).toBeInTheDocument();
  });
});
