import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  CreditCard,
  Plus,
  Search,
  CheckCircle2,
  Clock,
  PauseCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  payrollApi,
  type StaffLoan,
  type StaffSalaryProfile,
} from "@/features/payroll/api/payrollApi";
import {
  staffLoanSchema,
  type StaffLoanFormData,
} from "@/features/payroll/schemas/payrollSchemas";

export default function StaffLoansPage() {
  const { t } = useTranslation();

  const [loans, setLoans] = useState<StaffLoan[]>([]);
  const [profiles, setProfiles] = useState<StaffSalaryProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const form = useForm<StaffLoanFormData>({
    resolver: zodResolver(staffLoanSchema),
    defaultValues: {
      staff: "",
      loan_type: "advance",
      principal_amount: 10000,
      monthly_installment: 2000,
      reason: "",
    },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [loansRes, profRes] = await Promise.all([
        payrollApi.getLoans({ status: statusFilter === "all" ? undefined : statusFilter }),
        payrollApi.getProfiles(),
      ]);
      setLoans(loansRes.results || []);
      setProfiles(profRes.results || []);
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.loadLoansFailed", "Failed to load staff loans and advances."),
      });
    } finally {
      setLoading(false);
    }
  }, [statusFilter, t]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleFormSubmit = async (data: StaffLoanFormData) => {
    try {
      await payrollApi.createLoan({
        staff: data.staff,
        loan_type: data.loan_type,
        principal_amount: data.principal_amount.toString(),
        monthly_installment: data.monthly_installment.toString(),
        reason: data.reason,
      });
      setIsModalOpen(false);
      form.reset();
      setNotification({
        type: "success",
        message: t("payroll.loanCreatedSuccess", "Staff loan/advance recorded successfully."),
      });
      void fetchData();
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.loanCreateFailed", "Failed to record staff loan."),
      });
    }
  };

  const filteredLoans = loans.filter(
    (l) =>
      l.staff_employee_id.toLowerCase().includes(search.toLowerCase()) ||
      l.staff_name_en.toLowerCase().includes(search.toLowerCase()) ||
      (l.reason && l.reason.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <CreditCard className="h-6 w-6 text-emerald-600" />
            {t("payroll.loansTitle", "Staff Loans & Salary Advances")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t(
              "payroll.loansSubtitle",
              "Track welfare loans, emergency salary advances, and automated monthly payroll deductions."
            )}
          </p>
        </div>

        <Button
          onClick={() => setIsModalOpen(true)}
          className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
        >
          <Plus className="h-4 w-4" />
          {t("payroll.issueLoanBtn", "Issue Loan / Advance")}
        </Button>
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

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("common.search", "Search by Staff ID, name, reason...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <span>{t("common.status", "Status")}:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 px-2 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
            >
              <option value="all">All Loans</option>
              <option value="active">Active Recovery</option>
              <option value="completed">Completed / Settled</option>
              <option value="paused">Paused</option>
            </select>
          </label>
        </div>
      </div>

      {/* Loans Table */}
      <div className="border rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">{t("staff.employeeId", "Staff ID")}</th>
                <th className="py-3 px-4">{t("common.name", "Employee Name")}</th>
                <th className="py-3 px-4">{t("payroll.loanType", "Category")}</th>
                <th className="py-3 px-4">{t("payroll.principal", "Principal (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.installment", "Monthly Ded. (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.recovered", "Recovered (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.remaining", "Remaining (৳)")}</th>
                <th className="py-3 px-4">{t("common.status", "Status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading staff loans...")}
                  </td>
                </tr>
              ) : filteredLoans.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    {t("payroll.noLoansFound", "No loans or advances recorded.")}
                  </td>
                </tr>
              ) : (
                filteredLoans.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-mono font-semibold text-xs text-slate-700 dark:text-slate-300">
                      {l.staff_employee_id}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">
                      {l.staff_name_en}
                    </td>
                    <td className="py-3 px-4">
                      <span className="capitalize font-semibold text-xs text-slate-700 dark:text-slate-300">
                        {l.loan_type === "advance" ? "Salary Advance" : "Institutional Loan"}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
                      ৳{Number(l.principal_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-rose-600">
                      ৳{Number(l.monthly_installment).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-emerald-600">
                      ৳{Number(l.total_recovered).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs font-bold text-amber-700 dark:text-amber-400">
                      ৳{Number(l.remaining_balance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4">
                      {l.status === "active" ? (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-semibold">
                          <Clock className="h-3 w-3" /> Active
                        </span>
                      ) : l.status === "completed" ? (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 font-semibold">
                          <CheckCircle2 className="h-3 w-3" /> Settled
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 font-semibold">
                          <PauseCircle className="h-3 w-3" /> Paused
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Issue Loan Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.issueLoanModalTitle", "Disburse Staff Loan / Advance")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void form.handleSubmit(handleFormSubmit)(e);
            }}
            className="space-y-4"
          >
            <FormField>
              <FormLabel>{t("staff.selectStaff", "Staff Member")}</FormLabel>
              <select
                {...form.register("staff")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="">-- Choose Employee --</option>
                {profiles.map((p) => (
                  <option key={p.staff} value={p.staff}>
                    {p.staff_employee_id} - {p.staff_name_en}
                  </option>
                ))}
              </select>
              {form.formState.errors.staff && (
                <FormMessage>{form.formState.errors.staff.message}</FormMessage>
              )}
            </FormField>

            <FormField>
              <FormLabel>{t("payroll.loanType", "Category")}</FormLabel>
              <select
                {...form.register("loan_type")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="advance">Salary Advance (অগ্রিম বেতন)</option>
                <option value="loan">Institutional Loan (কল্যাণ তহবিল ঋণ)</option>
              </select>
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.principal", "Principal Amount (৳)")}</FormLabel>
                <Input
                  type="number"
                  step="100"
                  {...form.register("principal_amount", { valueAsNumber: true })}
                />
              </FormField>

              <FormField>
                <FormLabel>{t("payroll.installment", "Monthly Installment (৳)")}</FormLabel>
                <Input
                  type="number"
                  step="100"
                  {...form.register("monthly_installment", { valueAsNumber: true })}
                />
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.loanReason", "Purpose / Reason")}</FormLabel>
              <Input
                placeholder="e.g. Medical emergency or advance against Eid salary"
                {...form.register("reason")}
              />
            </FormField>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("common.save", "Record Loan")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
