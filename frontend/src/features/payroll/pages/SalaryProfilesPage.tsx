import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Users,
  Search,
  Building,
  Edit,
  Landmark,
  Smartphone,
  CheckCircle2,
  Plus,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  payrollApi,
  type StaffSalaryProfile,
  type SalaryStructure,
} from "@/features/payroll/api/payrollApi";
import { staffApi, type StaffListItem } from "@/features/staff/api/staffApi";
import {
  staffSalaryProfileSchema,
  createStaffSalaryProfileSchema,
  type StaffSalaryProfileFormData,
  type CreateStaffSalaryProfileFormData,
} from "@/features/payroll/schemas/payrollSchemas";

export default function SalaryProfilesPage() {
  const { t } = useTranslation();

  const [profiles, setProfiles] = useState<StaffSalaryProfile[]>([]);
  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [staffList, setStaffList] = useState<StaffListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [structureFilter, setStructureFilter] = useState<string>("all");
  const [isSyncing, setIsSyncing] = useState(false);

  // Modals state
  const [selectedProfile, setSelectedProfile] = useState<StaffSalaryProfile | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);
  const [profileToDelete, setProfileToDelete] = useState<StaffSalaryProfile | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Notification state
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Edit Form
  const form = useForm<StaffSalaryProfileFormData>({
    resolver: zodResolver(staffSalaryProfileSchema),
    defaultValues: {
      structure: null,
      basic_salary: 0,
      mpo_portion: 0,
      institutional_portion: 0,
      payment_method: "bank_transfer",
      bank_name: "",
      bank_branch: "",
      bank_account_number: "",
      bank_routing_number: "",
      mfs_number: "",
      pf_enrolled: false,
      pf_employee_percent: 10,
    },
  });

  // Create Form
  const createForm = useForm<CreateStaffSalaryProfileFormData>({
    resolver: zodResolver(createStaffSalaryProfileSchema),
    defaultValues: {
      staff: "",
      structure: null,
      basic_salary: 0,
      mpo_portion: 0,
      institutional_portion: 0,
      payment_method: "bank_transfer",
      bank_name: "",
      bank_branch: "",
      bank_account_number: "",
      bank_routing_number: "",
      mfs_number: "",
      pf_enrolled: false,
      pf_employee_percent: 10,
    },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [profRes, structRes, staffRes] = await Promise.all([
        payrollApi.getProfiles(),
        payrollApi.getStructures(),
        staffApi.getStaffList({ status: "active" }).catch(() => ({ results: [] as StaffListItem[] })),
      ]);
      setProfiles(profRes.results || []);
      setStructures(structRes.results || []);
      setStaffList(staffRes.results || []);
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.loadProfilesFailed", "Failed to load staff salary profiles."),
      });
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // Sync Staff Roster
  const handleSyncRoster = async () => {
    setIsSyncing(true);
    try {
      const res = await payrollApi.syncStaffRoster();
      setNotification({
        type: "success",
        message: res.message || t("payroll.syncSuccess", "Staff roster synchronized to salary profiles."),
      });
      void fetchData();
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.syncFailed", "Failed to synchronize staff roster."),
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Open Edit Modal
  const handleEditClick = (profile: StaffSalaryProfile) => {
    setSelectedProfile(profile);
    form.reset({
      structure: profile.structure || null,
      basic_salary: Number(profile.basic_salary) || 0,
      mpo_portion: Number(profile.mpo_portion) || 0,
      institutional_portion: Number(profile.institutional_portion) || 0,
      payment_method: profile.payment_method,
      bank_name: profile.bank_name || "",
      bank_branch: profile.bank_branch || "",
      bank_account_number: profile.bank_account_number || "",
      bank_routing_number: profile.bank_routing_number || "",
      mfs_number: profile.mfs_number || "",
      pf_enrolled: profile.pf_enrolled,
      pf_employee_percent: Number(profile.pf_employee_percent) || 10,
    });
    setIsEditModalOpen(true);
  };

  // Edit Form Submit
  const handleFormSubmit = async (data: StaffSalaryProfileFormData) => {
    if (!selectedProfile) return;
    try {
      await payrollApi.updateProfile(selectedProfile.id, {
        structure: data.structure || null,
        basic_salary: data.basic_salary.toString(),
        mpo_portion: data.mpo_portion ? data.mpo_portion.toString() : "0.00",
        institutional_portion: data.institutional_portion
          ? data.institutional_portion.toString()
          : "0.00",
        payment_method: data.payment_method,
        bank_name: data.bank_name,
        bank_branch: data.bank_branch,
        bank_account_number: data.bank_account_number,
        bank_routing_number: data.bank_routing_number,
        mfs_number: data.mfs_number,
        pf_enrolled: data.pf_enrolled,
        pf_employee_percent: data.pf_employee_percent
          ? data.pf_employee_percent.toString()
          : "10.00",
      });
      setIsEditModalOpen(false);
      setNotification({
        type: "success",
        message: t("payroll.profileUpdated", "Staff salary profile updated successfully."),
      });
      void fetchData();
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.profileUpdateFailed", "Failed to update salary profile."),
      });
    }
  };

  // Create Form Submit
  const handleCreateSubmit = async (data: CreateStaffSalaryProfileFormData) => {
    setIsSubmittingCreate(true);
    try {
      await payrollApi.createProfile({
        staff: data.staff,
        structure: data.structure || null,
        basic_salary: data.basic_salary.toString(),
        mpo_portion: data.mpo_portion ? data.mpo_portion.toString() : "0.00",
        institutional_portion: data.institutional_portion
          ? data.institutional_portion.toString()
          : "0.00",
        payment_method: data.payment_method,
        bank_name: data.bank_name,
        bank_branch: data.bank_branch,
        bank_account_number: data.bank_account_number,
        bank_routing_number: data.bank_routing_number,
        mfs_number: data.mfs_number,
        pf_enrolled: data.pf_enrolled,
        pf_employee_percent: data.pf_employee_percent
          ? data.pf_employee_percent.toString()
          : "10.00",
      });
      setIsCreateModalOpen(false);
      createForm.reset();
      setNotification({
        type: "success",
        message: t("payroll.profileCreated", "Staff salary profile created and structure assigned successfully."),
      });
      void fetchData();
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.profileCreateFailed", "Failed to create staff salary profile."),
      });
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  // Delete Form Submit
  const handleConfirmDelete = async () => {
    if (!profileToDelete) return;
    setIsDeleting(true);
    try {
      await payrollApi.deleteProfile(profileToDelete.id);
      setIsDeleteModalOpen(false);
      setProfileToDelete(null);
      setNotification({
        type: "success",
        message: t("payroll.profileDeleted", "Staff salary profile removed successfully."),
      });
      void fetchData();
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.profileDeleteFailed", "Failed to remove staff salary profile."),
      });
    } finally {
      setIsDeleting(false);
    }
  };

  // Staff members who don't have a profile yet
  const profiledStaffIds = new Set(profiles.map((p) => p.staff));
  const unprofiledStaff = staffList.filter((s) => !profiledStaffIds.has(s.id));

  const filteredProfiles = profiles.filter((p) => {
    const matchesSearch =
      p.staff_employee_id.toLowerCase().includes(search.toLowerCase()) ||
      p.staff_name_en.toLowerCase().includes(search.toLowerCase()) ||
      (p.staff_name_bn && p.staff_name_bn.includes(search));

    if (!matchesSearch) return false;

    if (structureFilter === "missing") {
      return !p.structure;
    }
    if (structureFilter === "assigned") {
      return !!p.structure;
    }
    if (structureFilter !== "all") {
      return p.structure === structureFilter;
    }
    return true;
  });

  const watchedEditMethod = form.watch("payment_method");
  const watchedCreateMethod = createForm.watch("payment_method");

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Users className="h-6 w-6 text-emerald-600" />
            {t("payroll.profilesTitle", "Staff Salary Profiles")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t(
              "payroll.profilesSubtitle",
              "Manage employee compensation baseline, salary structure templates, MPO subvention, and banking accounts."
            )}
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            onClick={() => { void handleSyncRoster(); }}
            disabled={isSyncing}
            className="gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
          >
            <RefreshCw className={`h-4 w-4 ${isSyncing ? "animate-spin" : ""}`} />
            {isSyncing
              ? t("payroll.syncing", "Syncing Roster...")
              : t("payroll.syncStaffRoster", "Sync Staff Roster")}
          </Button>
          <Button
            onClick={() => {
              createForm.reset({
                staff: unprofiledStaff[0]?.id ?? "",
                structure: structures[0]?.id ?? null,
                basic_salary: 0,
                mpo_portion: 0,
                institutional_portion: 0,
                payment_method: "bank_transfer",
                bank_name: "",
                bank_branch: "",
                bank_account_number: "",
                bank_routing_number: "",
                mfs_number: "",
                pf_enrolled: false,
                pf_employee_percent: 10,
              });
              setIsCreateModalOpen(true);
            }}
            className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
          >
            <Plus className="h-4 w-4" />
            {t("payroll.assignSalaryProfile", "Assign Salary Profile")}
          </Button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          role="alert"
          className={`p-3 rounded-lg flex items-center justify-between text-sm ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300"
          }`}
        >
          <span>{notification.message}</span>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex flex-1 items-center gap-3 w-full sm:max-w-xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              placeholder={t("common.search", "Search by Staff ID, name...")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={structureFilter}
            onChange={(e) => setStructureFilter(e.target.value)}
            className="h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 shrink-0"
          >
            <option value="all">{t("payroll.allStructures", "All Structures")}</option>
            <option value="missing">{t("payroll.missingStructure", "⚠️ No Structure Assigned")}</option>
            <option value="assigned">{t("payroll.hasStructure", "✓ Has Structure")}</option>
            {structures.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        </div>
        <div className="text-sm text-slate-500 font-medium">
          {t("common.total", "Showing")}:{" "}
          <span className="font-bold text-slate-900 dark:text-slate-100">
            {filteredProfiles.length}
          </span>{" "}
          / {profiles.length} {t("staff.staffMembers", "staff")}
        </div>
      </div>

      {/* Profiles Table */}
      <div className="border rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">{t("staff.employeeId", "Staff ID")}</th>
                <th className="py-3 px-4">{t("common.name", "Employee Name")}</th>
                <th className="py-3 px-4">{t("payroll.structure", "Salary Structure")}</th>
                <th className="py-3 px-4">{t("payroll.basicSalary", "Basic (মূল)")}</th>
                <th className="py-3 px-4">{t("payroll.mpoPortion", "MPO / School")}</th>
                <th className="py-3 px-4">{t("payroll.paymentMode", "Disbursement")}</th>
                <th className="py-3 px-4">{t("payroll.pf", "PF")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading salary profiles...")}
                  </td>
                </tr>
              ) : filteredProfiles.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center">
                    <div className="max-w-md mx-auto space-y-3">
                      <Users className="h-10 w-10 text-slate-400 mx-auto" />
                      <div>
                        <p className="font-semibold text-base text-slate-700 dark:text-slate-300">
                          {t("payroll.noProfilesFound", "No staff salary profiles matching your query.")}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {t(
                            "payroll.noProfilesPrompt",
                            "Click 'Sync Staff Roster' to automatically import all active school employees into payroll profiles, or assign a structure individually."
                          )}
                        </p>
                      </div>
                      <div className="flex items-center justify-center gap-2 pt-2">
                        <Button
                          variant="outline"
                          onClick={() => { void handleSyncRoster(); }}
                          disabled={isSyncing}
                          className="gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950"
                        >
                          <Sparkles className="h-4 w-4" />
                          {isSyncing ? t("payroll.syncing", "Syncing...") : t("payroll.syncStaffRoster", "Sync Staff Roster")}
                        </Button>
                        <Button
                          onClick={() => {
                            createForm.reset({
                              staff: unprofiledStaff[0]?.id ?? "",
                              structure: structures[0]?.id ?? null,
                              basic_salary: 0,
                              mpo_portion: 0,
                              institutional_portion: 0,
                              payment_method: "bank_transfer",
                              bank_name: "",
                              bank_branch: "",
                              bank_account_number: "",
                              bank_routing_number: "",
                              mfs_number: "",
                              pf_enrolled: false,
                              pf_employee_percent: 10,
                            });
                            setIsCreateModalOpen(true);
                          }}
                          className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
                        >
                          <Plus className="h-4 w-4" />
                          {t("payroll.assignSalaryProfile", "Assign Salary Profile")}
                        </Button>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredProfiles.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-mono font-semibold text-xs text-slate-700 dark:text-slate-300">
                      {p.staff_employee_id}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-900 dark:text-slate-100">
                        {p.staff_name_en}
                      </div>
                      {p.staff_name_bn && (
                        <div className="text-xs text-slate-500">{p.staff_name_bn}</div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {p.structure_name ? (
                        <span className="font-semibold text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                          {p.structure_name}
                        </span>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEditClick(p)}
                          className="h-6 px-2 text-xs font-semibold text-amber-700 bg-amber-50 border-amber-200 hover:bg-amber-100 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800 gap-1"
                          title={t("payroll.assignStructurePrompt", "Click to assign a salary structure")}
                        >
                          <Plus className="h-3 w-3" />
                          {t("payroll.assignStructure", "Assign Structure")}
                        </Button>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-xs text-emerald-700 dark:text-emerald-400">
                      ৳{Number(p.basic_salary).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono">
                      {Number(p.mpo_portion) > 0 ? (
                        <span className="text-blue-700 dark:text-blue-400">
                          Govt: ৳{Number(p.mpo_portion).toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-slate-500">Non-MPO</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      <span className="inline-flex items-center gap-1.5 capitalize font-medium text-slate-700 dark:text-slate-300">
                        {p.payment_method === "bank_transfer" ? (
                          <>
                            <Landmark className="h-3.5 w-3.5 text-blue-600" />
                            {p.bank_name ? `${p.bank_name} (${p.bank_account_number?.slice(-4) || ""})` : "Bank Transfer"}
                          </>
                        ) : p.payment_method === "mfs" ? (
                          <>
                            <Smartphone className="h-3.5 w-3.5 text-rose-600" />
                            MFS ({p.mfs_number || "bKash/Nagad"})
                          </>
                        ) : (
                          <>
                            <Building className="h-3.5 w-3.5 text-slate-500" />
                            Cash in Hand
                          </>
                        )}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {p.pf_enrolled ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Yes
                        </span>
                      ) : (
                        <span className="text-slate-400">No</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditClick(p)}
                          className="h-8 w-8 p-0 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                          title={t("common.edit", "Edit Compensation Profile")}
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setProfileToDelete(p);
                            setIsDeleteModalOpen(true);
                          }}
                          className="h-8 w-8 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                          title={t("common.delete", "Delete Salary Profile")}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal 1: Create / Assign Salary Profile */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-600" />
              {t("payroll.assignProfileTitle", "Assign Salary Structure to Employee")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void createForm.handleSubmit(handleCreateSubmit)(e);
            }}
            className="space-y-4"
          >
            {/* Employee Selector */}
            <FormField>
              <FormLabel>{t("staff.selectEmployee", "Select Employee (কর্মকর্তা/শিক্ষক)")}</FormLabel>
              <select
                {...createForm.register("staff")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                required
              >
                <option value="" disabled>
                  -- {t("staff.chooseStaff", "Choose an active employee")} --
                </option>
                {staffList.map((s) => {
                  const hasProfile = profiledStaffIds.has(s.id);
                  return (
                    <option key={s.id} value={s.id} disabled={hasProfile}>
                      {s.employee_id} - {s.full_name_en} {s.department_name ? `(${s.department_name})` : ""}{" "}
                      {hasProfile ? "(Already Profiled)" : ""}
                    </option>
                  );
                })}
              </select>
              {createForm.formState.errors.staff && (
                <FormMessage>{createForm.formState.errors.staff.message}</FormMessage>
              )}
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.basicSalary", "Monthly Basic (মূল বেতন ৳)")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="e.g. 30000"
                  {...createForm.register("basic_salary", { valueAsNumber: true })}
                />
                {createForm.formState.errors.basic_salary && (
                  <FormMessage>{createForm.formState.errors.basic_salary.message}</FormMessage>
                )}
              </FormField>

              <FormField>
                <FormLabel>{t("payroll.structure", "Salary Structure Template")}</FormLabel>
                <select
                  {...createForm.register("structure")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="">-- No Structure / Custom --</option>
                  {structures.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </FormField>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.mpoPortion", "Govt. MPO Portion (৳)")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  {...createForm.register("mpo_portion", { valueAsNumber: true })}
                />
              </FormField>

              <FormField>
                <FormLabel>{t("payroll.institutionalPortion", "School Top-Up (৳)")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  {...createForm.register("institutional_portion", { valueAsNumber: true })}
                />
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.paymentMode", "Disbursement Channel")}</FormLabel>
              <select
                {...createForm.register("payment_method")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="bank_transfer">Bank Transfer / BEFTN (ব্যাংক)</option>
                <option value="mfs">Mobile Financial Service (bKash / Nagad)</option>
                <option value="cash">Cash in Hand (নগদ)</option>
                <option value="cheque">Bank Cheque (চেক)</option>
              </select>
            </FormField>

            {watchedCreateMethod === "bank_transfer" && (
              <div className="p-3 border rounded-lg bg-slate-50 dark:bg-slate-800/40 space-y-3">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  BEFTN Electronic Bank Details
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <FormField>
                    <FormLabel>{t("payroll.bankName", "Bank Name")}</FormLabel>
                    <Input placeholder="e.g. Sonali Bank PLC" {...createForm.register("bank_name")} />
                  </FormField>
                  <FormField>
                    <FormLabel>{t("payroll.bankBranch", "Branch Name")}</FormLabel>
                    <Input placeholder="e.g. Uttara Branch" {...createForm.register("bank_branch")} />
                  </FormField>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <FormField>
                    <FormLabel>{t("payroll.accountNo", "Account Number")}</FormLabel>
                    <Input placeholder="e.g. 0123456789012" {...createForm.register("bank_account_number")} />
                  </FormField>
                  <FormField>
                    <FormLabel>{t("payroll.routingNo", "Routing Number (9 Digits)")}</FormLabel>
                    <Input placeholder="e.g. 200261234" {...createForm.register("bank_routing_number")} />
                  </FormField>
                </div>
              </div>
            )}

            {watchedCreateMethod === "mfs" && (
              <div className="p-3 border rounded-lg bg-slate-50 dark:bg-slate-800/40">
                <FormField>
                  <FormLabel>{t("payroll.mfsWalletNo", "MFS Wallet Number (+8801...)")}</FormLabel>
                  <Input placeholder="+8801712345678" {...createForm.register("mfs_number")} />
                </FormField>
              </div>
            )}

            <div className="flex items-center gap-4 pt-2">
              <label className="flex items-center gap-2 text-sm font-medium cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  {...createForm.register("pf_enrolled")}
                />
                <span>{t("payroll.enrolledPf", "Enrolled in Provident Fund (PF)")}</span>
              </label>
            </div>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                type="submit"
                disabled={isSubmittingCreate}
                className="bg-emerald-700 hover:bg-emerald-800 text-white"
              >
                {isSubmittingCreate ? t("common.saving", "Saving...") : t("payroll.assignProfileBtn", "Assign Profile")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 2: Edit Profile Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.editProfileTitle", "Configure Compensation Profile")} —{" "}
              {selectedProfile?.staff_name_en}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void form.handleSubmit(handleFormSubmit)(e);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.basicSalary", "Monthly Basic (মূল বেতন ৳)")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  {...form.register("basic_salary", { valueAsNumber: true })}
                />
                {form.formState.errors.basic_salary && (
                  <FormMessage>{form.formState.errors.basic_salary.message}</FormMessage>
                )}
              </FormField>

              <FormField>
                <FormLabel>{t("payroll.structure", "Salary Structure Template")}</FormLabel>
                <select
                  {...form.register("structure")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="">-- No Structure / Custom --</option>
                  {structures.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </FormField>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.mpoPortion", "Govt. MPO Portion (৳)")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  {...form.register("mpo_portion", { valueAsNumber: true })}
                />
              </FormField>

              <FormField>
                <FormLabel>{t("payroll.institutionalPortion", "School Top-Up (৳)")}</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  {...form.register("institutional_portion", { valueAsNumber: true })}
                />
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.paymentMode", "Disbursement Channel")}</FormLabel>
              <select
                {...form.register("payment_method")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="bank_transfer">Bank Transfer / BEFTN (ব্যাংক)</option>
                <option value="mfs">Mobile Financial Service (bKash / Nagad)</option>
                <option value="cash">Cash in Hand (নগদ)</option>
                <option value="cheque">Bank Cheque (চেক)</option>
              </select>
            </FormField>

            {watchedEditMethod === "bank_transfer" && (
              <div className="p-3 border rounded-lg bg-slate-50 dark:bg-slate-800/40 space-y-3">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  BEFTN Electronic Bank Details
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <FormField>
                    <FormLabel>{t("payroll.bankName", "Bank Name")}</FormLabel>
                    <Input placeholder="e.g. Sonali Bank PLC" {...form.register("bank_name")} />
                  </FormField>
                  <FormField>
                    <FormLabel>{t("payroll.bankBranch", "Branch Name")}</FormLabel>
                    <Input placeholder="e.g. Uttara Branch" {...form.register("bank_branch")} />
                  </FormField>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <FormField>
                    <FormLabel>{t("payroll.accountNo", "Account Number")}</FormLabel>
                    <Input placeholder="e.g. 0123456789012" {...form.register("bank_account_number")} />
                  </FormField>
                  <FormField>
                    <FormLabel>{t("payroll.routingNo", "Routing Number (9 Digits)")}</FormLabel>
                    <Input placeholder="e.g. 200261234" {...form.register("bank_routing_number")} />
                  </FormField>
                </div>
              </div>
            )}

            {watchedEditMethod === "mfs" && (
              <div className="p-3 border rounded-lg bg-slate-50 dark:bg-slate-800/40">
                <FormField>
                  <FormLabel>{t("payroll.mfsWalletNo", "MFS Wallet Number (+8801...)")}</FormLabel>
                  <Input placeholder="+8801712345678" {...form.register("mfs_number")} />
                </FormField>
              </div>
            )}

            <div className="flex items-center gap-4 pt-2">
              <label className="flex items-center gap-2 text-sm font-medium cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  {...form.register("pf_enrolled")}
                />
                <span>{t("payroll.enrolledPf", "Enrolled in Provident Fund (PF)")}</span>
              </label>
            </div>

            <DialogFooter className="pt-3">
              <Button type="button" variant="outline" onClick={() => setIsEditModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.save", "Save Changes")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 3: Delete Confirmation Modal */}
      <Dialog open={isDeleteModalOpen} onOpenChange={setIsDeleteModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
              {t("payroll.deleteProfileTitle", "Delete Staff Salary Profile")}
            </DialogTitle>
          </DialogHeader>

          <div className="py-2 text-sm text-slate-600 dark:text-slate-300 space-y-2">
            <p>
              {t(
                "payroll.confirmDeleteProfile",
                "Are you sure you want to remove this employee salary profile? They will no longer be included in automated payroll runs until re-profiled."
              )}
            </p>
            {profileToDelete && (
              <div className="p-2.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-xs text-slate-800 dark:text-slate-200">
                {profileToDelete.staff_employee_id} — {profileToDelete.staff_name_en}
              </div>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isDeleting}
            >
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              type="button"
              onClick={() => { void handleConfirmDelete(); }}
              disabled={isDeleting}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              {isDeleting ? t("common.deleting", "Deleting...") : t("common.delete", "Delete Profile")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
