import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import { StaffListPage } from "@/features/staff/pages/StaffListPage";
import { StaffIDCardPreview } from "@/features/staff/components/StaffIDCardPreview";
import type { StaffDetail } from "@/features/staff/api/staffApi";

const mockStaffMembers = [
  {
    id: "staff-sa",
    employee_id: "EMP-2026-000",
    full_name_en: "System Superadmin",
    full_name_bn: "সিস্টেম সুপারঅ্যাডমিন",
    department: "dept-2",
    department_name: "Administration",
    designation: "desig-sa",
    designation_title: "Super Admin",
    staff_type: "superadmin",
    user_type: "superadmin",
    status: "active",
    phone: "+8801700112233",
    email: "sa@example.com",
    nid: "19801234567890123",
    joining_date: "2019-01-01",
    is_mpo: false,
    mpo_index_number: null,
    photo: null,
  },
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
    user_type: "teacher",
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
    user_type: "accountant",
    status: "active",
    phone: "+8801812345678",
    email: "shamima@example.com",
    nid: "19901234567890123",
    joining_date: "2021-03-01",
    is_mpo: false,
    mpo_index_number: null,
    photo: null,
  },
  {
    id: "staff-3",
    employee_id: "EMP-2026-003",
    full_name_en: "Abul Kashem",
    full_name_bn: "আবুল কাশেম",
    department: "dept-2",
    department_name: "General Support",
    designation: "desig-3",
    designation_title: "Campus Driver",
    staff_type: "driver",
    user_type: "driver",
    status: "active",
    phone: "+8801912345678",
    email: "kashem@example.com",
    nid: "19921234567890123",
    joining_date: "2022-01-01",
    is_mpo: false,
    mpo_index_number: null,
    photo: null,
  },
];

function renderStaffListPage(userRole = "superadmin") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  useAuthStore.getState().setTokens("acc", "ref");
  useAuthStore.getState().setUser({
    id: "user-test",
    username: "tester",
    full_name: "Test User",
    phone: "+8801700000000",
    email: "tester@example.com",
    user_type: userRole,
    institution_id: "inst-1",
    roles: [userRole],
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
  afterEach(() => {
    server.resetHandlers();
  });

  beforeEach(() => {
    server.use(
      http.get("*/api/v1/staff/staff/summary/", () => {
        return HttpResponse.json({
          total: 4,
          superadmin: 1,
          admin: 1,
          teacher: 1,
          staff: 1,
        });
      }),
      http.get("*/api/v1/staff/departments/", () => {
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
      http.get("*/api/v1/staff/staff/", () => {
        return HttpResponse.json({
          count: mockStaffMembers.length,
          next: null,
          previous: null,
          results: mockStaffMembers,
        });
      }),
    );
  });

  it("renders employee directory with KPI cards and section-wise categorized tables for superadmin", async () => {
    renderStaffListPage("superadmin");

    // Check KPI cards
    await waitFor(() => {
      expect(screen.getAllByText("Super Admin").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Administration").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Teachers & Faculty").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Support Staff").length).toBeGreaterThan(0);
    });

    // Check Section Headers and members after list loads
    await waitFor(() => {
      expect(screen.getByText("Super Administrators")).toBeInTheDocument();
      expect(screen.getByText("Administrative Officers & Leadership")).toBeInTheDocument();
      expect(screen.getByText("Teaching Faculty & Educators")).toBeInTheDocument();
      expect(screen.getByText("Support & Facilities Personnel")).toBeInTheDocument();
      expect(screen.getByText("System Superadmin")).toBeInTheDocument();
      expect(screen.getByText("Md. Rafiqul Islam")).toBeInTheDocument();
      expect(screen.getByText("Shamima Akhter")).toBeInTheDocument();
      expect(screen.getByText("Abul Kashem")).toBeInTheDocument();
      expect(screen.getByText("MPO")).toBeInTheDocument();
    });
  });

  it("hides Super Admin KPI card and section for non-superadmin users", async () => {
    // Non-superadmin view (e.g. Teacher)
    server.use(
      http.get("*/api/v1/staff/staff/summary/", () => {
        return HttpResponse.json({
          total: 3,
          admin: 1,
          teacher: 1,
          staff: 1,
        });
      }),
      http.get("*/api/v1/staff/staff/", () => {
        // Backend excludes superadmin for non-superadmin callers
        return HttpResponse.json({
          count: 3,
          next: null,
          previous: null,
          results: mockStaffMembers.filter((m) => m.staff_type !== "superadmin"),
        });
      }),
    );

    renderStaffListPage("teacher");

    await waitFor(() => {
      expect(screen.getAllByText("Teachers & Faculty").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Administration").length).toBeGreaterThan(0);
    });

    // Super Admin KPI and Section MUST NOT exist
    expect(screen.queryByText("Super Administrators")).not.toBeInTheDocument();
    expect(screen.queryByText("System Superadmin")).not.toBeInTheDocument();
  });

  it("renders empty state when no staff match", async () => {
    server.use(
      http.get("*/api/v1/staff/staff/summary/", () => {
        return HttpResponse.json({
          total: 0,
          superadmin: 0,
          admin: 0,
          teacher: 0,
          staff: 0,
        });
      }),
      http.get("*/api/v1/staff/staff/", () => {
        return HttpResponse.json({
          count: 0,
          next: null,
          previous: null,
          results: [],
        });
      }),
    );

    renderStaffListPage("superadmin");

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
    shift_name: null,
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
    branch_name: "Main Campus",
    user_id: "user-1",
    username: "rafiq",
    user_type: "teacher",
    has_portal_access: true,
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
