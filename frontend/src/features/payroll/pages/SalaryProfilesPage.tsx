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
import {
  staffSalaryProfileSchema,
  type StaffSalaryProfileFormData,
} from "@/features/payroll/schemas/payrollSchemas";

export default function SalaryProfilesPage() {
  const { t } = useTranslation();

  const [profiles, setProfiles] = useState<StaffSalaryProfile[]>([]);
  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<StaffSalaryProfile | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

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

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [profRes, structRes] = await Promise.all([
        payrollApi.getProfiles(),
        payrollApi.getStructures(),
      ]);
      setProfiles(profRes.results || []);
      setStructures(structRes.results || []);
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

  const filteredProfiles = profiles.filter(
    (p) =>
      p.staff_employee_id.toLowerCase().includes(search.toLowerCase()) ||
      p.staff_name_en.toLowerCase().includes(search.toLowerCase()) ||
      (p.staff_name_bn && p.staff_name_bn.includes(search))
  );

  const watchedMethod = form.watch("payment_method");

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
              "Manage employee compensation baseline, MPO subvention, banking BEFTN accounts, and payment channels."
            )}
          </p>
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

      {/* Search & Stats Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("common.search", "Search by Staff ID, name...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="text-sm text-slate-500 font-medium">
          {t("common.total", "Total Staff")}:{" "}
          <span className="font-bold text-slate-900 dark:text-slate-100">
            {profiles.length}
          </span>
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
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    {t("payroll.noProfilesFound", "No staff salary profiles matching your query.")}
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
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          {p.structure_name}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">Custom Base</span>
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
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleEditClick(p)}
                        className="h-8 gap-1 text-xs text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
                      >
                        <Edit className="h-3.5 w-3.5" />
                        {t("common.edit", "Edit")}
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Profile Modal */}
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

            {watchedMethod === "bank_transfer" && (
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

            {watchedMethod === "mfs" && (
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
    </div>
  );
}
