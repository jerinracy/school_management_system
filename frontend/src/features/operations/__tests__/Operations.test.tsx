import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";

import { HomeworkListPage } from "../pages/HomeworkListPage";
import { HomeworkSubmissionsPage } from "../pages/HomeworkSubmissionsPage";
import { LibraryCatalogPage } from "../pages/LibraryCatalogPage";
import { LibraryCirculationPage } from "../pages/LibraryCirculationPage";
import { TransportFleetPage } from "../pages/TransportFleetPage";
import { TransportRoutesPage } from "../pages/TransportRoutesPage";
import { HostelDormsPage } from "../pages/HostelDormsPage";
import { HostelAllocationsPage } from "../pages/HostelAllocationsPage";

const mockAssignments = [
  {
    id: "hw-1",
    title: "Algebra Quadratic Equations Problem Set",
    description: "Solve problems 1 to 20 from Chapter 4.",
    class_level_name: "Class 10",
    section_name: "Section A",
    subject_name: "General Mathematics",
    due_at: "2026-11-20T23:59:00Z",
    max_marks: 25,
    status: "published",
    allow_late_submission: true,
    submission_count: 32,
    created_at: "2026-11-15T08:00:00Z",
  },
  {
    id: "hw-2",
    title: "Bengali Grammar Essay: Digital Bangladesh",
    description: "Write an essay within 500 words.",
    class_level_name: "Class 9",
    section_name: "Section B",
    subject_name: "Bangla 2nd Paper",
    due_at: "2026-11-25T23:59:00Z",
    max_marks: 20,
    status: "draft",
    allow_late_submission: false,
    submission_count: 0,
    created_at: "2026-11-15T09:00:00Z",
  },
];

const mockSubmissions = [
  {
    id: "sub-1",
    homework: "hw-1",
    student: "std-1",
    student_name: "Rahim Chowdhury",
    student_roll: "1001",
    submitted_at: "2026-11-16T14:30:00Z",
    is_late: false,
    marks_obtained: 22,
    feedback: "Well demonstrated working steps.",
    status: "graded",
  },
];

const mockBooks = [
  {
    id: "bk-1",
    title: "Advanced Physics for Higher Secondary",
    title_bn: "উচ্চ মাধ্যমিক পদার্থবিজ্ঞান",
    authors: "Dr. Shahjahan Tapan",
    isbn: "978-984-1234-56-7",
    category: "Science",
    publisher: "Hasan Book House",
    edition: "12th Edition",
    total_copies: 15,
    available_copies: 11,
    is_reference_only: false,
  },
];

const mockIssues = [
  {
    id: "issue-1",
    copy: "copy-1",
    book_title: "Advanced Physics for Higher Secondary",
    member: "mem-1",
    member_name: "Tanvir Ahmed",
    member_card: "LIB-ST-1042",
    issue_date: "2026-11-01",
    due_date: "2026-11-15",
    returned_date: null,
    status: "issued",
    fine_amount: "0.00",
  },
];

const mockFines = [
  {
    id: "fine-1",
    issue: "issue-2",
    book_title: "Chemistry Vol 1",
    member: "mem-2",
    card_number: "LIB-ST-1088",
    amount: "50.00",
    overdue_days: 5,
    status: "unpaid",
  },
];

const mockVehicles = [
  {
    id: "veh-1",
    registration_no: "DHAKA-METRO-GA-11-2233",
    vehicle_type: "bus",
    capacity: 52,
    make_model: "Hino AK1J 2022",
    fitness_expiry: "2026-12-31",
    tax_token_expiry: "2026-12-15",
    route_permit_expiry: "2027-06-30",
    status: "active",
  },
];

const mockDrivers = [
  {
    id: "drv-1",
    staff_name: "Abdul Karim",
    license_no: "DL-DH-998877",
    license_expiry: "2028-04-10",
    contact_phone: "+8801712345678",
    helper_name: "Kalam Mia",
    helper_phone: "+8801812345678",
    status: "active",
  },
];

const mockRoutes = [
  {
    id: "route-1",
    name: "Uttara to Dhanmondi Campus",
    code: "R-01",
    vehicle_registration: "DHAKA-METRO-GA-11-2233",
    driver_name: "Abdul Karim",
    monthly_fee: "2500.00",
    is_active: true,
    stops: [
      {
        id: "stop-1",
        name: "Uttara House Building",
        sequence: 1,
        pickup_time: "07:00",
        drop_time: "14:30",
        fare: "2500.00",
      },
    ],
  },
];

const mockHostels = [
  {
    id: "hostel-1",
    name: "Dr. Muhammad Shahidullah Hall",
    name_bn: "ড. মুহম্মদ শহীদুল্লাহ্ হল",
    code: "SH-01",
    hostel_type: "boys",
    warden_name: "Prof. Anisuzzaman",
    warden_phone: "+8801911223344",
    curfew_time: "21:00:00",
    address: "North Campus, Gate 2",
    is_active: true,
  },
];

const mockRooms = [
  {
    id: "rm-1",
    hostel: "hostel-1",
    room_number: "204",
    floor: 2,
    capacity: 4,
    monthly_fee: "3500.00",
  },
];

const mockBeds = [
  { id: "bed-1", room: "rm-1", bed_number: "204-A", status: "occupied" },
  { id: "bed-2", room: "rm-1", bed_number: "204-B", status: "available" },
];

const mockAllocations = [
  {
    id: "alloc-1",
    student: "std-1",
    student_name: "Shafiqul Islam",
    hostel_name: "Dr. Muhammad Shahidullah Hall",
    room: "204",
    bed: "204-A",
    allocated_date: "2026-01-10",
    is_active: true,
  },
];

const mockGatePasses = [
  {
    id: "gp-1",
    student: "std-1",
    student_name: "Shafiqul Islam",
    hostel: "hostel-1",
    reason: "Family medical visit",
    destination: "Cumilla",
    out_time: "2026-11-15T15:00:00Z",
    expected_return_at: "2026-11-17T18:00:00Z",
    actual_return_at: null,
    status: "approved",
  },
];

function renderWithClient(ui: React.ReactElement, initialRoute = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Task F13 - Institutional Operations & Student Services Dashboard", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: "usr-ops-admin",
        username: "opsadmin",
        email: "operations@school.edu.bd",
        phone: "+8801700000000",
        user_type: "admin",
        institution_id: "inst-1",
        roles: ["admin"],
        permissions: [
          "homework.view",
          "homework.manage",
          "library.view",
          "library.manage",
          "transport.view",
          "transport.manage",
          "hostel.view",
          "hostel.manage",
        ],
        full_name: "Operations Administrator",
      },
      accessToken: "mock-token",
      refreshToken: "mock-refresh",
      isAuthenticated: true,
    });

    server.use(
      // Homework
      http.get("/api/v1/homework/assignments/", () => {
        return HttpResponse.json({ results: mockAssignments, count: mockAssignments.length });
      }),
      http.get("/api/v1/homework/assignments/:id/", ({ params }) => {
        const item = mockAssignments.find((a) => a.id === params.id) || mockAssignments[0];
        return HttpResponse.json(item);
      }),
      http.get("/api/v1/homework/submissions/", () => {
        return HttpResponse.json({ results: mockSubmissions, count: mockSubmissions.length });
      }),
      // Library
      http.get("/api/v1/library/books/", () => {
        return HttpResponse.json({ results: mockBooks, count: mockBooks.length });
      }),
      http.get("/api/v1/library/issues/", () => {
        return HttpResponse.json({ results: mockIssues, count: mockIssues.length });
      }),
      http.get("/api/v1/library/fines/", () => {
        return HttpResponse.json({ results: mockFines, count: mockFines.length });
      }),
      // Transport
      http.get("/api/v1/transport/vehicles/", () => {
        return HttpResponse.json({ results: mockVehicles, count: mockVehicles.length });
      }),
      http.get("/api/v1/transport/drivers/", () => {
        return HttpResponse.json({ results: mockDrivers, count: mockDrivers.length });
      }),
      http.get("/api/v1/transport/routes/", () => {
        return HttpResponse.json({ results: mockRoutes, count: mockRoutes.length });
      }),
      // Hostel
      http.get("/api/v1/hostel/hostels/", () => {
        return HttpResponse.json({ results: mockHostels, count: mockHostels.length });
      }),
      http.get("/api/v1/hostel/rooms/", () => {
        return HttpResponse.json({ results: mockRooms, count: mockRooms.length });
      }),
      http.get("/api/v1/hostel/beds/", () => {
        return HttpResponse.json({ results: mockBeds, count: mockBeds.length });
      }),
      http.get("/api/v1/hostel/allocations/", () => {
        return HttpResponse.json({ results: mockAllocations, count: mockAllocations.length });
      }),
      http.get("/api/v1/hostel/gate-passes/", () => {
        return HttpResponse.json({ results: mockGatePasses, count: mockGatePasses.length });
      }),
      // Common lookups
      http.get("/api/v1/academics/classes/", () => {
        return HttpResponse.json({ results: [{ id: "cls-10", name: "Class 10" }] });
      }),
      http.get("/api/v1/academics/subjects/", () => {
        return HttpResponse.json({ results: [{ id: "sub-math", name: "General Mathematics" }] });
      }),
      http.get("/api/v1/students/", () => {
        return HttpResponse.json({ results: [{ id: "std-1", full_name: "Rahim Chowdhury", roll_number: "1001" }] });
      })
    );
  });

  it("renders homework assignment roster and allows toggling create modal", async () => {
    renderWithClient(<HomeworkListPage />);

    expect(await screen.findByText(/Algebra Quadratic Equations Problem Set/i)).toBeInTheDocument();
    expect(screen.getByText(/General Mathematics/i)).toBeInTheDocument();
    expect(screen.getByText(/25/i)).toBeInTheDocument();

    const createBtn = screen.getByRole("button", { name: /Create Assignment/i });
    expect(createBtn).toBeInTheDocument();
    fireEvent.click(createBtn);

    expect(await screen.findByText(/Create Homework Assignment/i)).toBeInTheDocument();
  });

  it("renders homework student submissions review queue and grading modal", async () => {
    renderWithClient(
      <Routes>
        <Route path="/operations/homework/:id/submissions" element={<HomeworkSubmissionsPage />} />
      </Routes>,
      "/operations/homework/hw-1/submissions"
    );

    expect(await screen.findByText(/Rahim Chowdhury/i)).toBeInTheDocument();
    expect(screen.getByText(/22 \/ 25/i)).toBeInTheDocument();

    const gradeBtn = screen.getByRole("button", { name: /Update Grade/i });
    expect(gradeBtn).toBeInTheDocument();
    fireEvent.click(gradeBtn);

    expect(await screen.findByText(/Grade Submission:/i)).toBeInTheDocument();
  });

  it("renders library catalog and circulation desk with fines ledger", async () => {
    renderWithClient(<LibraryCatalogPage />);

    expect(await screen.findByText(/Advanced Physics for Higher Secondary/i)).toBeInTheDocument();
    expect(screen.getByText(/Dr. Shahjahan Tapan/i)).toBeInTheDocument();
    expect(screen.getByText(/978-984-1234-56-7/i)).toBeInTheDocument();

    const addBookBtn = screen.getByRole("button", { name: /Add New Book/i });
    expect(addBookBtn).toBeInTheDocument();
    fireEvent.click(addBookBtn);
    expect(await screen.findByText(/Catalog New Book/i)).toBeInTheDocument();
  });

  it("renders circulation active book loans and overdue fines", async () => {
    renderWithClient(<LibraryCirculationPage />);

    expect(await screen.findByText(/Advanced Physics for Higher Secondary/i)).toBeInTheDocument();
    expect(screen.getByText("mem-1")).toBeInTheDocument();

    // Switch to Fines tab
    const finesTab = screen.getByRole("button", { name: /Overdue Fines Ledger/i });
    fireEvent.click(finesTab);

    expect(await screen.findByText(/LIB-ST-1088/i)).toBeInTheDocument();
    expect(screen.getByText(/5 days/i)).toBeInTheDocument();
    expect(screen.getByText(/৳50.00/i)).toBeInTheDocument();
  });

  it("renders transport vehicle fleet and driver credentials", async () => {
    renderWithClient(<TransportFleetPage />);

    expect(await screen.findByText(/DHAKA-METRO-GA-11-2233/i)).toBeInTheDocument();
    expect(screen.getByText(/Hino AK1J 2022/i)).toBeInTheDocument();
    expect(screen.getByText(/52 Seats/i)).toBeInTheDocument();

    // Switch to drivers tab
    const driversTab = screen.getByRole("button", { name: /Drivers & Helpers Roster/i });
    fireEvent.click(driversTab);

    expect(await screen.findByText(/Abdul Karim/i)).toBeInTheDocument();
    expect(screen.getByText(/DL-DH-998877/i)).toBeInTheDocument();
    expect(screen.getByText(/Kalam Mia/i)).toBeInTheDocument();
  });

  it("renders transport routes with stops and monthly fare", async () => {
    renderWithClient(<TransportRoutesPage />);

    expect(await screen.findByText(/Uttara to Dhanmondi Campus/i)).toBeInTheDocument();
    expect(screen.getByText(/R-01/i)).toBeInTheDocument();
    expect(screen.getByText(/Uttara House Building/i)).toBeInTheDocument();
    expect(screen.getByText(/৳2500.00/i)).toBeInTheDocument();
  });

  it("renders hostel dormitory building directory and occupancy matrix", async () => {
    renderWithClient(<HostelDormsPage />);

    expect(await screen.findByText(/Dr. Muhammad Shahidullah Hall/i)).toBeInTheDocument();
    expect(screen.getByText(/Curfew: 21:00:00/i)).toBeInTheDocument();
    expect(screen.getByText(/Room 204/i)).toBeInTheDocument();
    expect(await screen.findByText(/204-A/i)).toBeInTheDocument();
    expect(screen.getByText(/204-B/i)).toBeInTheDocument();
  });

  it("renders hostel resident allocations and gate pass out-leaves", async () => {
    renderWithClient(<HostelAllocationsPage />);

    expect(await screen.findByText(/Shafiqul Islam/i)).toBeInTheDocument();
    expect(screen.getByText(/Dr. Muhammad Shahidullah Hall/i)).toBeInTheDocument();
    expect(screen.getByText(/Room: 204/i)).toBeInTheDocument();
    expect(screen.getByText("204-A")).toBeInTheDocument();

    // Switch to Gate Passes tab
    const gatePassTab = screen.getByRole("button", { name: /Gate Pass Out-Leaves/i });
    fireEvent.click(gatePassTab);

    expect(await screen.findByText(/Family medical visit/i)).toBeInTheDocument();
    expect(screen.getByText(/Cumilla/i)).toBeInTheDocument();
  });
});
