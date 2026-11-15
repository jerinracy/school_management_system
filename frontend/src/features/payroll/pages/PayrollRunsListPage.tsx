import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Wallet,
  Plus,
  ArrowRight,
  TrendingUp,
  DollarSign,
  Users,
  CheckCircle2,
  Clock,
  Lock,
  FileCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  payrollApi,
  type PayrollRun,
  type PayrollRunStatus,
} from "@/features/payroll/api/payrollApi";
import {
  generatePayrollRunSchema,
  type GeneratePayrollRunFormData,
} from "@/features/payroll/schemas/payrollSchemas";

const MONTH_NAMES_EN = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const MONTH_NAMES_BN = [
  "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
  "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"
];

export default function PayrollRunsListPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const isBn = i18n.language === "bn";

  const currentDate = new Date();
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState<number>(currentDate.getFullYear());
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const form = useForm<GeneratePayrollRunFormData>({
    resolver: zodResolver(generatePayrollRunSchema),
    defaultValues: {
      year: currentDate.getFullYear(),
      month: currentDate.getMonth() + 1,
      title: "",
      working_days_in_month: 26,
      absence_deduction_basis: "basic",
    },
  });

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await payrollApi.getPayrollRuns({
        year: selectedYear,
        status: statusFilter === "all" ? undefined : statusFilter,
      });
      setRuns(res.results || []);
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.loadRunsFailed", "Failed to load monthly payroll runs."),
      });
    } finally {
      setLoading(false);
    }
  }, [selectedYear, statusFilter, t]);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  const handleGenerateSubmit = async (data: GeneratePayrollRunFormData) => {
    try {
      const generated = await payrollApi.generatePayrollRun({
        ...data,
        title: data.title || `Salary Sheet - ${MONTH_NAMES_EN[data.month]} ${data.year}`,
      });
      setIsGenerateModalOpen(false);
      setNotification({
        type: "success",
        message: t("payroll.runGeneratedSuccess", "Monthly payroll calculated successfully."),
      });
      void navigate(`/payroll/runs/${generated.id}`);
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.runGenerateFailed", "Failed to generate monthly payroll run."),
      });
    }
  };

  // Aggregated KPI calculations
  const totalGross = runs.reduce((acc, r) => acc + Number(r.total_gross || 0), 0);
  const totalDeductions = runs.reduce((acc, r) => acc + Number(r.total_deductions || 0), 0);
  const totalNet = runs.reduce((acc, r) => acc + Number(r.total_net_pay || 0), 0);
  const totalPayslips = runs.reduce((acc, r) => acc + (r.payslips_count || 0), 0);

  const getStatusBadge = (status: PayrollRunStatus, isLocked: boolean) => {
    if (isLocked) {
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
          <Lock className="h-3 w-3" /> Locked
        </span>
      );
    }
    switch (status) {
      case "draft":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <Clock className="h-3 w-3" /> Draft
          </span>
        );
      case "reviewed":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
            <FileCheck className="h-3 w-3" /> Reviewed
          </span>
        );
      case "approved":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
            <CheckCircle2 className="h-3 w-3" /> Approved
          </span>
        );
      case "paid":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <CheckCircle2 className="h-3 w-3" /> Paid / Disbursed
          </span>
        );
      default:
        return <span className="text-xs uppercase font-medium">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Wallet className="h-6 w-6 text-emerald-600" />
            {t("payroll.runsTitle", "Staff Payroll & Salary Sheets")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t(
              "payroll.runsSubtitle",
              "Biometric attendance-linked monthly salary batches, BEFTN advice sheets, and festival bonus processing."
            )}
          </p>
        </div>

        <Button
          onClick={() => setIsGenerateModalOpen(true)}
          className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
        >
          <Plus className="h-4 w-4" />
          {t("payroll.generateRunBtn", "Generate Monthly Payroll")}
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

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">
              {t("payroll.totalGrossPay", "Total Gross Earnings")}
            </span>
            <TrendingUp className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100 mt-2">
            ৳{totalGross.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-400 mt-1">{t("payroll.allRunsYear", "Year total")}</p>
        </div>

        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">
              {t("payroll.totalDeductions", "Total Deductions")}
            </span>
            <DollarSign className="h-4 w-4 text-rose-500" />
          </div>
          <div className="text-xl font-bold font-mono text-rose-600 dark:text-rose-400 mt-2">
            ৳{totalDeductions.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-400 mt-1">{t("payroll.absenceLoanPf", "Absence, Loans & PF")}</p>
        </div>

        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm border-emerald-200 dark:border-emerald-800/50 bg-emerald-50/20 dark:bg-emerald-950/10">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 uppercase">
              {t("payroll.netDisbursed", "Net Salary Disbursed")}
            </span>
            <Wallet className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="text-xl font-black font-mono text-emerald-700 dark:text-emerald-400 mt-2">
            ৳{totalNet.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-emerald-600/80 mt-1">{t("payroll.netPayout", "Disbursed via Bank/MFS")}</p>
        </div>

        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">
              {t("payroll.totalPayslips", "Total Payslips")}
            </span>
            <Users className="h-4 w-4 text-blue-500" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100 mt-2">
            {totalPayslips}
          </div>
          <p className="text-xs text-slate-400 mt-1">{t("payroll.vouchersIssued", "Generated vouchers")}</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <span>{t("common.year", "Year")}:</span>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="h-9 px-2 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
            >
              {[2024, 2025, 2026, 2027].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <span>{t("common.status", "Status")}:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 px-2 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
            >
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="reviewed">Reviewed</option>
              <option value="approved">Approved</option>
              <option value="paid">Paid</option>
              <option value="locked">Locked</option>
            </select>
          </label>
        </div>

        <div className="text-xs text-slate-400">
          Showing {runs.length} payroll run(s)
        </div>
      </div>

      {/* Runs Table */}
      <div className="border rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">{t("payroll.period", "Payroll Period")}</th>
                <th className="py-3 px-4">{t("payroll.batchTitle", "Batch Title")}</th>
                <th className="py-3 px-4">{t("common.status", "Status")}</th>
                <th className="py-3 px-4">{t("payroll.workingDays", "Working Days")}</th>
                <th className="py-3 px-4">{t("payroll.grossAmount", "Gross (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.deductions", "Deductions (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.netPayout", "Net Payable (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.payslips", "Slips")}</th>
                <th className="py-3 px-4">{t("payroll.glVoucher", "GL Voucher")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading payroll runs...")}
                  </td>
                </tr>
              ) : runs.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    {t("payroll.noRunsFound", "No payroll runs created for this year.")}
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-100">
                      {isBn ? `${MONTH_NAMES_BN[r.month]} ${r.year}` : `${MONTH_NAMES_EN[r.month]} ${r.year}`}
                    </td>
                    <td className="py-3 px-4 text-xs font-medium text-slate-600 dark:text-slate-300">
                      {r.title}
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(r.status, r.is_locked)}</td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-600 dark:text-slate-400">
                      {r.working_days_in_month} d
                    </td>
                    <td className="py-3 px-4 font-mono text-xs">
                      ৳{Number(r.total_gross).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-rose-600">
                      ৳{Number(r.total_deductions).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-xs text-emerald-700 dark:text-emerald-400">
                      ৳{Number(r.total_net_pay).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs font-semibold">{r.payslips_count}</td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-500">
                      {r.journal_entry_voucher_no || <span className="text-slate-400">-</span>}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        size="sm"
                        onClick={() => { void navigate(`/payroll/runs/${r.id}`); }}
                        className="h-8 gap-1 text-xs bg-emerald-700 hover:bg-emerald-800 text-white"
                      >
                        {t("payroll.manageRun", "Workspace")}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Generate Payroll Run Modal */}
      <Dialog open={isGenerateModalOpen} onOpenChange={setIsGenerateModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {t("payroll.generateRunModalTitle", "Calculate Monthly Payroll")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void form.handleSubmit(handleGenerateSubmit)(e);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("common.year", "Year")}</FormLabel>
                <Input
                  type="number"
                  {...form.register("year", { valueAsNumber: true })}
                />
              </FormField>
              <FormField>
                <FormLabel>{t("common.month", "Month")}</FormLabel>
                <select
                  {...form.register("month", { valueAsNumber: true })}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  {MONTH_NAMES_EN.slice(1).map((m, idx) => (
                    <option key={m} value={idx + 1}>
                      {isBn ? MONTH_NAMES_BN[idx + 1] : m}
                    </option>
                  ))}
                </select>
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("payroll.runTitleLabel", "Payroll Run Title")}</FormLabel>
              <Input
                placeholder="e.g. Regular Staff Salary - July 2026"
                {...form.register("title")}
              />
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("payroll.workingDays", "Working Days in Month")}</FormLabel>
                <Input
                  type="number"
                  {...form.register("working_days_in_month", { valueAsNumber: true })}
                />
              </FormField>
              <FormField>
                <FormLabel>{t("payroll.absenceDeductionBasis", "Absence Deduction Basis")}</FormLabel>
                <select
                  {...form.register("absence_deduction_basis")}
                  className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                >
                  <option value="basic">Pro-rata Basic Salary</option>
                  <option value="gross">Pro-rata Gross Salary</option>
                </select>
              </FormField>
            </div>

            <p className="text-xs text-slate-500 bg-slate-50 dark:bg-slate-800 p-2.5 rounded border">
              {t(
                "payroll.biometricLinkNotice",
                "Attendance engine punches and approved leaves for this period will automatically calculate pro-rata salary deductions and staff loan installments."
              )}
            </p>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsGenerateModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {t("payroll.calculateNow", "Calculate Sheet")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
