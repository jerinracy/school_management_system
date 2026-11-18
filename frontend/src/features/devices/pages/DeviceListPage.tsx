import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Fingerprint,
  HardDrive,
  HelpCircle,
  ListOrdered,
  Plus,
  RefreshCw,
  Search,
  Server,
  Signal,
  Wifi,
  WifiOff,
  X,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  devicesApi,
  type DeviceItem,
  type RawPunchItem,
} from "@/features/devices/api/devicesApi";
import {
  deviceTerminalSchema,
  type DeviceTerminalFormData,
} from "@/features/devices/schemas/deviceSchemas";
import { studentsApi } from "@/features/students/api/studentsApi";
import { staffApi } from "@/features/staff/api/staffApi";

type ActiveTab = "terminals" | "punches" | "unmapped" | "commands";

export default function DeviceListPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<ActiveTab>("terminals");
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState<DeviceItem | null>(null);
  const [resolvingPunch, setResolvingPunch] = useState<RawPunchItem | null>(null);
  const [selectedResolveUserType, setSelectedResolveUserType] = useState<"student" | "staff">("student");
  const [selectedResolvePersonId, setSelectedResolvePersonId] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const { data: terminalsData, isLoading: isTerminalsLoading, refetch: refetchTerminals } = useQuery({
    queryKey: ["devices-terminals", search],
    queryFn: () => devicesApi.getTerminals({ search: search.trim() || undefined }),
  });

  const { data: punchesData, isLoading: isPunchesLoading, refetch: refetchPunches } = useQuery({
    queryKey: ["devices-punches"],
    queryFn: () => devicesApi.getRawPunches(),
    enabled: activeTab === "punches",
  });

  const { data: unmappedData, isLoading: isUnmappedLoading, refetch: refetchUnmapped } = useQuery({
    queryKey: ["devices-unmapped"],
    queryFn: () => devicesApi.getUnmappedPunches(),
    enabled: activeTab === "unmapped",
  });

  const { data: commandsData, isLoading: isCommandsLoading, refetch: refetchCommands } = useQuery({
    queryKey: ["devices-commands"],
    queryFn: () => devicesApi.getCommands(),
    enabled: activeTab === "commands",
  });

  const { data: studentsData } = useQuery({
    queryKey: ["devices-students-lookup"],
    queryFn: () => studentsApi.getStudents({ status: "active" }),
    enabled: Boolean(resolvingPunch) && selectedResolveUserType === "student",
  });

  const { data: staffData } = useQuery({
    queryKey: ["devices-staff-lookup"],
    queryFn: () => staffApi.getStaffList({ status: "active" }),
    enabled: Boolean(resolvingPunch) && selectedResolveUserType === "staff",
  });

  // Terminal Form
  const {
    register: registerTerminal,
    handleSubmit: handleTerminalSubmit,
    reset: resetTerminal,
    formState: { errors: terminalErrors, isSubmitting: isTerminalSubmitting },
  } = useForm<DeviceTerminalFormData>({
    resolver: zodResolver(deviceTerminalSchema) as never,
    defaultValues: {
      name: "",
      vendor: "ZKTeco",
      model: "SpeedFace-V5L",
      serial_no: "",
      device_type: "fingerprint",
      protocol: "push_adms",
      ip_address: "192.168.1.201",
      port: 4370,
      location: "Main Gate",
      is_active: true,
    },
  });

  // Create / Update Terminal Mutation
  const saveTerminalMutation = useMutation({
    mutationFn: (data: DeviceTerminalFormData) => {
      if (editingDevice) {
        return devicesApi.updateTerminal(editingDevice.id, {
          name: data.name,
          vendor: data.vendor,
          model: data.model || undefined,
          serial_no: data.serial_no || undefined,
          device_type: data.device_type,
          protocol: data.protocol,
          ip_address: data.ip_address || undefined,
          port: data.port,
          location: data.location || undefined,
          is_active: data.is_active,
        });
      }
      return devicesApi.createTerminal({
        name: data.name,
        vendor: data.vendor,
        model: data.model || undefined,
        serial_no: data.serial_no || "",
        device_type: data.device_type,
        protocol: data.protocol,
        ip_address: data.ip_address || undefined,
        port: data.port,
        location: data.location || undefined,
        is_active: data.is_active,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["devices-terminals"] });
      setShowAddModal(false);
      setEditingDevice(null);
      resetTerminal();
      setActionMessage(t("devices.savedSuccess", "Terminal saved successfully."));
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError((err as Error).message || "Failed to save device terminal.");
    },
  });

  // Test Connection Mutation
  const testConnMutation = useMutation({
    mutationFn: (id: string) => devicesApi.testConnection(id),
    onSuccess: (data: DeviceItem) => {
      void queryClient.invalidateQueries({ queryKey: ["devices-terminals"] });
      setActionMessage(`Ping successful! ${data.name} is ONLINE (latency < 2ms).`);
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError((err as Error).message || "Connection test failed.");
    },
  });

  // Resolve Punch Mutation
  const resolvePunchMutation = useMutation({
    mutationFn: ({ punchId, personId, userType }: { punchId: string; personId: string; userType: "student" | "staff" }) => {
      const payload = userType === "student" ? { student_id: personId } : { staff_id: personId };
      return devicesApi.resolveUnmappedPunch(punchId, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["devices-unmapped"] });
      void queryClient.invalidateQueries({ queryKey: ["devices-punches"] });
      setResolvingPunch(null);
      setSelectedResolvePersonId("");
      setActionMessage(t("devices.punchResolved", "Punch mapped to user profile successfully."));
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError((err as Error).message || "Failed to resolve unmapped punch.");
    },
  });

  const terminals = terminalsData?.results ?? [];
  const punches = punchesData?.results ?? [];
  const unmappedPunches = unmappedData?.results ?? [];
  const commands = commandsData?.results ?? [];
  const students = studentsData?.results ?? [];
  const staffMembers = staffData?.results ?? [];

  const onlineCount = terminals.filter((d) => d.status === "online").length;
  const offlineCount = terminals.filter((d) => d.status !== "online").length;

  const handleRefresh = () => {
    if (activeTab === "terminals") void refetchTerminals();
    if (activeTab === "punches") void refetchPunches();
    if (activeTab === "unmapped") void refetchUnmapped();
    if (activeTab === "commands") void refetchCommands();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {t("devices.title", "Biometric Hardware Terminals & Attendance Intakes")}
          </h1>
          <p className="text-xs text-slate-500">
            {t(
              "devices.subtitle",
              "Manage ZKTeco, Hikvision, Realtime terminals, monitor ADMS push protocols, and raw punch streams."
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="h-9 gap-1.5 text-xs rounded-lg"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>{t("common.refresh", "Refresh")}</span>
          </Button>

          <Button
            size="sm"
            onClick={() => {
              setEditingDevice(null);
              resetTerminal();
              setShowAddModal(true);
            }}
            className="gap-2 bg-emerald-800 text-xs hover:bg-emerald-900 text-white rounded-lg h-9 shadow-xs"
          >
            <Plus className="h-4 w-4" />
            <span>{t("devices.addTerminal", "Register Terminal")}</span>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900 flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500 block">
              {t("devices.totalTerminals", "Configured Terminals")}
            </span>
            <span className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
              {terminals.length}
            </span>
          </div>
          <div className="h-10 w-10 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-800 dark:text-emerald-400">
            <Server className="h-5 w-5" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900 flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500 block">
              {t("devices.onlineTerminals", "Online Terminals")}
            </span>
            <span className="text-2xl font-bold font-mono text-emerald-700 dark:text-emerald-400">
              {onlineCount}
            </span>
          </div>
          <div className="h-10 w-10 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-700">
            <Wifi className="h-5 w-5" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900 flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500 block">
              {t("devices.offlineTerminals", "Offline / Silent")}
            </span>
            <span className="text-2xl font-bold font-mono text-amber-700 dark:text-amber-400">
              {offlineCount}
            </span>
          </div>
          <div className="h-10 w-10 rounded-lg bg-amber-50 dark:bg-amber-950/40 flex items-center justify-center text-amber-600">
            <WifiOff className="h-5 w-5" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900 flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500 block">
              {t("devices.unmappedPunches", "Unmapped Punches")}
            </span>
            <span className="text-2xl font-bold font-mono text-rose-700 dark:text-rose-400">
              {unmappedPunches.length}
            </span>
          </div>
          <div className="h-10 w-10 rounded-lg bg-rose-50 dark:bg-rose-950/40 flex items-center justify-center text-rose-600">
            <HelpCircle className="h-5 w-5" />
          </div>
        </div>
      </div>

      {/* Notifications */}
      {actionMessage && (
        <div className="flex items-center justify-between rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-emerald-600 hover:text-emerald-800">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="flex items-center justify-between rounded-lg bg-rose-50 p-3 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-rose-600 hover:text-rose-800">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Tabs & Search */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-1">
          <button
            onClick={() => setActiveTab("terminals")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "terminals"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Cpu className="h-4 w-4" />
            {t("devices.tabTerminals", "Hardware Inventory")}
          </button>

          <button
            onClick={() => setActiveTab("punches")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "punches"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Activity className="h-4 w-4" />
            {t("devices.tabPunches", "Raw Punch Stream")}
          </button>

          <button
            onClick={() => setActiveTab("unmapped")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "unmapped"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Fingerprint className="h-4 w-4 text-rose-600" />
            {t("devices.tabUnmapped", "Unmapped Resolver")}
            {unmappedPunches.length > 0 && (
              <span className="rounded-full bg-rose-100 px-1.5 py-0.2 text-[10px] font-bold text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                {unmappedPunches.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("commands")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === "commands"
                ? "border-emerald-700 text-emerald-800 dark:border-emerald-500 dark:text-emerald-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <ListOrdered className="h-4 w-4" />
            {t("devices.tabCommands", "Command Queue")}
          </button>
        </div>

        {activeTab === "terminals" && (
          <div className="relative w-64">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("devices.searchPlaceholder", "Search terminals by name/IP...")}
              className="pl-8 text-xs h-8 rounded-lg"
            />
          </div>
        )}
      </div>

      {/* Tab 1: Terminals Inventory */}
      {activeTab === "terminals" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {isTerminalsLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            </div>
          ) : terminals.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("devices.noTerminals", "No biometric terminals registered.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("devices.terminal", "Terminal Name")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.vendorModel", "Brand & Model")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.network", "Network Address")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.protocol", "Protocol")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.location", "Zone / Location")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.status", "Status")}</th>
                    <th className="px-4 py-3 font-semibold text-right">{t("common.actions", "Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {terminals.map((d) => (
                    <tr key={d.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3">
                        <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                          <HardDrive className="h-4 w-4 text-emerald-700" />
                          <span>{d.name}</span>
                        </div>
                        <p className="text-[10px] font-mono text-slate-400">
                          S/N: {d.serial_no || "—"}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        <span className="font-semibold">{d.vendor}</span> {d.model}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                        {d.ip_address || "DHCP"}{d.port ? `:${d.port}` : ""}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-mono text-[11px] bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-700 dark:text-slate-300 uppercase">
                          {d.protocol}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {d.location || "General Gate"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            d.status === "online"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              d.status === "online" ? "bg-emerald-600 animate-pulse" : "bg-slate-400"
                            }`}
                          />
                          {d.status === "online" ? "Online" : "Offline"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={testConnMutation.isPending}
                            onClick={() => testConnMutation.mutate(d.id)}
                            className="h-7 px-2 text-[11px] text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800 border-emerald-300 rounded-md"
                          >
                            <Signal className="h-3 w-3 mr-1" />
                            {t("devices.testConn", "Test Ping")}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setEditingDevice(d);
                              resetTerminal({
                                name: d.name,
                                vendor: d.vendor,
                                model: d.model || "",
                                serial_no: d.serial_no || "",
                                device_type: d.device_type,
                                protocol: d.protocol,
                                ip_address: d.ip_address || "",
                                port: d.port || undefined,
                                location: d.location || "",
                                is_active: d.is_active,
                              });
                              setShowAddModal(true);
                            }}
                            className="h-7 px-2 text-[11px] text-slate-600"
                          >
                            {t("common.edit", "Edit")}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Raw Punch Stream */}
      {activeTab === "punches" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {isPunchesLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            </div>
          ) : punches.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("devices.noPunches", "No raw punch events recorded in stream.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("devices.punchTime", "Device Timestamp")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.terminal", "Terminal")}</th>
                    <th className="px-4 py-3 font-semibold font-mono">{t("devices.rawPin", "Raw PIN / ID")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.verifyMode", "Verify Mode")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.resolvedPerson", "Mapped Person")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.status", "Ingestion Status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {punches.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-mono text-slate-700 dark:text-slate-300">
                        {p.device_time}
                      </td>
                      <td className="px-4 py-3 text-slate-900 dark:text-slate-100 font-medium">
                        {p.device_name || "Device"}
                      </td>
                      <td className="px-4 py-3 font-mono font-bold text-emerald-800 dark:text-emerald-400">
                        {p.raw_user_id}
                      </td>
                      <td className="px-4 py-3 capitalize text-slate-600 dark:text-slate-400">
                        {p.verify_type}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">
                        {p.student_name ? (
                          <span>{p.student_name} (Student)</span>
                        ) : p.staff_name ? (
                          <span>{p.staff_name} (Staff)</span>
                        ) : (
                          <span className="text-rose-600 font-semibold">Unmapped</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                            p.status === "processed"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                              : p.status === "unmapped"
                              ? "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                              : "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Unmapped Resolver */}
      {activeTab === "unmapped" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {isUnmappedLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            </div>
          ) : unmappedPunches.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("devices.noUnmappedPunches", "All biometric punches are cleanly mapped to enrolled users.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("devices.punchTime", "Timestamp")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.terminal", "Terminal")}</th>
                    <th className="px-4 py-3 font-semibold font-mono">{t("devices.unmappedPin", "Unmapped PIN")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.verifyMode", "Verify Mode")}</th>
                    <th className="px-4 py-3 font-semibold text-right">{t("common.actions", "Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {unmappedPunches.map((up) => (
                    <tr key={up.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-400">
                        {up.device_time}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        {up.device_name || "Device"}
                      </td>
                      <td className="px-4 py-3 font-mono font-bold text-rose-700 dark:text-rose-400">
                        {up.raw_user_id}
                      </td>
                      <td className="px-4 py-3 capitalize text-slate-600 dark:text-slate-400">
                        {up.verify_type}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          onClick={() => {
                            setResolvingPunch(up);
                            setSelectedResolveUserType("student");
                            setSelectedResolvePersonId("");
                          }}
                          className="h-7 px-2.5 text-xs bg-emerald-800 hover:bg-emerald-900 text-white rounded-md"
                        >
                          <Fingerprint className="h-3 w-3 mr-1" />
                          {t("devices.resolveMap", "Map to Person")}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Command Queue */}
      {activeTab === "commands" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {isCommandsLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            </div>
          ) : commands.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              {t("devices.noCommands", "No pending device sync commands in queue.")}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("devices.commandType", "Command")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.terminal", "Terminal")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.status", "Status")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.sentAt", "Sent Time")}</th>
                    <th className="px-4 py-3 font-semibold">{t("devices.response", "Device Response")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {commands.map((cmd) => (
                    <tr key={cmd.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-mono font-bold text-slate-900 dark:text-slate-100">
                        {cmd.command_type}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {cmd.device_name || "Terminal"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                            cmd.status === "acknowledged"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                              : cmd.status === "failed"
                              ? "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                              : "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                          }`}
                        >
                          {cmd.status === "acknowledged" && <CheckCircle2 className="h-3 w-3" />}
                          {cmd.status === "failed" && <XCircle className="h-3 w-3" />}
                          {cmd.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-500">
                        {cmd.sent_at || "Queued"}
                      </td>
                      <td className="px-4 py-3 text-slate-500 max-w-[250px] truncate">
                        {cmd.response_message || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: Add / Edit Terminal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-emerald-700" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {editingDevice
                    ? t("devices.editTerminal", "Edit Biometric Terminal")
                    : t("devices.addTerminal", "Register Hardware Terminal")}
                </h2>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                void handleTerminalSubmit((data) => saveTerminalMutation.mutate(data))(e);
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("devices.terminalName", "Terminal Name")} *
                </label>
                <Input
                  {...registerTerminal("name")}
                  placeholder="e.g. Main Gate Terminal A"
                  className="h-9 text-xs"
                />
                {terminalErrors.name && (
                  <p className="mt-1 text-[11px] text-rose-600">{terminalErrors.name.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.vendor", "Brand / Vendor")} *
                  </label>
                  <select
                    {...registerTerminal("vendor")}
                    className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="ZKTeco">ZKTeco</option>
                    <option value="Hikvision">Hikvision</option>
                    <option value="Realtime">Realtime</option>
                    <option value="Dahua">Dahua</option>
                    <option value="Suprema">Suprema</option>
                    <option value="Anviz">Anviz</option>
                    <option value="Generic">Generic</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.model", "Model Name")}
                  </label>
                  <Input
                    {...registerTerminal("model")}
                    placeholder="e.g. SpeedFace-V5L"
                    className="h-9 text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.protocol", "Communication Protocol")} *
                  </label>
                  <select
                    {...registerTerminal("protocol")}
                    className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="push_adms">Push ADMS (Cloud Push)</option>
                    <option value="generic_http">Generic HTTP Webhook</option>
                    <option value="mqtt">MQTT IoT Broker</option>
                    <option value="pull_sdk">Pull SDK (LAN Polling)</option>
                    <option value="simulator">Hardware Simulator</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.verifyType", "Primary Verify Type")} *
                  </label>
                  <select
                    {...registerTerminal("device_type")}
                    className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option value="fingerprint">Fingerprint</option>
                    <option value="face">Facial Recognition</option>
                    <option value="rfid">RFID Proximity Card</option>
                    <option value="palm">Palm Vein</option>
                    <option value="qr">Dynamic QR Code</option>
                    <option value="pin">Numeric PIN</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.ipAddress", "IP Address")}
                  </label>
                  <Input
                    {...registerTerminal("ip_address")}
                    placeholder="192.168.1.201"
                    className="h-9 text-xs font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.port", "Port")}
                  </label>
                  <Input
                    type="number"
                    {...registerTerminal("port")}
                    placeholder="4370"
                    className="h-9 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.location", "Zone / Location")}
                  </label>
                  <Input
                    {...registerTerminal("location")}
                    placeholder="e.g. Academic Block Gate 2"
                    className="h-9 text-xs"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                    {t("devices.serialNo", "Serial Number")}
                  </label>
                  <Input
                    {...registerTerminal("serial_no")}
                    placeholder="e.g. ZK9876543210"
                    className="h-9 text-xs font-mono uppercase"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAddModal(false)}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isTerminalSubmitting || saveTerminalMutation.isPending}
                  className="bg-emerald-800 hover:bg-emerald-900 text-white"
                >
                  {isTerminalSubmitting ? t("common.saving", "Saving...") : t("common.save", "Save Terminal")}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Resolve Unmapped Punch */}
      {resolvingPunch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Fingerprint className="h-4 w-4 text-emerald-700" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {t("devices.resolvePunchTitle", "Resolve Unmapped Punch")}
                </h2>
              </div>
              <button
                onClick={() => setResolvingPunch(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 space-y-1 text-xs">
              <p className="text-slate-500">
                {t("devices.punchInfo", "Device PIN")}: <span className="font-mono font-bold text-slate-900 dark:text-slate-100">{resolvingPunch.raw_user_id}</span>
              </p>
              <p className="text-slate-500">
                {t("devices.terminal", "Terminal")}: <span className="font-semibold text-slate-800 dark:text-slate-200">{resolvingPunch.device_name}</span>
              </p>
              <p className="text-slate-500 font-mono text-[11px]">
                {resolvingPunch.device_time}
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("devices.userCategory", "User Category")}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedResolveUserType("student");
                      setSelectedResolvePersonId("");
                    }}
                    className={`py-2 text-center rounded-lg border font-semibold ${
                      selectedResolveUserType === "student"
                        ? "border-emerald-700 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                        : "border-slate-200 text-slate-600 dark:border-slate-700"
                    }`}
                  >
                    Student
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedResolveUserType("staff");
                      setSelectedResolvePersonId("");
                    }}
                    className={`py-2 text-center rounded-lg border font-semibold ${
                      selectedResolveUserType === "staff"
                        ? "border-emerald-700 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                        : "border-slate-200 text-slate-600 dark:border-slate-700"
                    }`}
                  >
                    Staff / Teacher
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium">
                  {t("devices.selectPerson", "Select Individual Profile")} *
                </label>
                <select
                  value={selectedResolvePersonId}
                  onChange={(e) => setSelectedResolvePersonId(e.target.value)}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 text-xs focus:outline-hidden focus:ring-1 focus:ring-emerald-700 dark:border-slate-700 dark:bg-slate-900"
                >
                  <option value="">{t("devices.chooseProfile", "Choose person...")}</option>
                  {selectedResolveUserType === "student"
                    ? students.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name_en} ({s.student_id})
                        </option>
                      ))
                    : staffMembers.map((st) => (
                        <option key={st.id} value={st.id}>
                          {st.full_name_en} ({st.employee_id}) — {st.designation_title}
                        </option>
                      ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setResolvingPunch(null)}
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="sm"
                disabled={!selectedResolvePersonId || resolvePunchMutation.isPending}
                onClick={() => {
                  if (resolvingPunch && selectedResolvePersonId) {
                    resolvePunchMutation.mutate({
                      punchId: resolvingPunch.id,
                      personId: selectedResolvePersonId,
                      userType: selectedResolveUserType,
                    });
                  }
                }}
                className="bg-emerald-800 hover:bg-emerald-900 text-white"
              >
                {t("devices.confirmMap", "Confirm & Map PIN")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
