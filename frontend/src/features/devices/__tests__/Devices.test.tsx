import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/store/authStore";
import DeviceListPage from "@/features/devices/pages/DeviceListPage";

const mockTerminals = [
  {
    id: "dev-1",
    name: "Main Gate Ingress A",
    vendor: "ZKTeco",
    model: "SpeedFace-V5L",
    serial_no: "ZK12345678",
    protocol: "push_adms",
    device_type: "fingerprint",
    ip_address: "192.168.1.201",
    port: 4370,
    location: "Main Gate Entry",
    status: "online",
    is_active: true,
  },
  {
    id: "dev-2",
    name: "Staff Lounge Terminal",
    vendor: "Hikvision",
    model: "DS-K1T671MF",
    serial_no: "HK87654321",
    protocol: "generic_http",
    device_type: "face",
    ip_address: "192.168.1.205",
    port: 80,
    location: "Faculty Room",
    status: "offline",
    is_active: true,
  },
];

function renderDeviceListPage() {
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
    permissions: ["devices.view", "devices.manage"],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DeviceListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DeviceListPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/v1/devices/terminals/", () => {
        return HttpResponse.json({
          count: mockTerminals.length,
          next: null,
          previous: null,
          results: mockTerminals,
        });
      }),
      http.get("/api/v1/devices/unmapped-punches/", () => {
        return HttpResponse.json({
          count: 0,
          next: null,
          previous: null,
          results: [],
        });
      }),
    );
  });

  it("renders terminal hardware inventory cards and table", async () => {
    renderDeviceListPage();

    await waitFor(() => {
      expect(screen.getByText("Main Gate Ingress A")).toBeInTheDocument();
      expect(screen.getByText("Staff Lounge Terminal")).toBeInTheDocument();
    });

    expect(screen.getByText("SpeedFace-V5L")).toBeInTheDocument();
    expect(screen.getByText("DS-K1T671MF")).toBeInTheDocument();
    expect(screen.getByText(/192.168.1.201:4370/)).toBeInTheDocument();
  });

  it("renders empty state when no terminals exist", async () => {
    server.use(
      http.get("/api/v1/devices/terminals/", () => {
        return HttpResponse.json({
          count: 0,
          next: null,
          previous: null,
          results: [],
        });
      }),
    );

    renderDeviceListPage();

    await waitFor(() => {
      expect(screen.getByText("No biometric terminals registered.")).toBeInTheDocument();
    });
  });
});
