import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  CheckCircle2,
  Lock,
  Download,
  Gift,
  Eye,
  FileSpreadsheet,
  Wallet,
  Clock,
  Send,
  Building,
} from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  payrollApi,
  type PayrollRun,
  type Payslip,
} from "@/features/payroll/api/payrollApi";
import {
  applyBonusSchema,
  type ApplyBonusFormData,
} from "@/features/payroll/schemas/payrollSchemas";
import { PayslipVoucherModal } from "../components/PayslipVoucherModal";

const MONTH_NAMES_EN = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const MONTH_NAMES_BN = [
  "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
  "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"
];

export default function PayrollRunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const isBn = i18n.language === "bn";

  const [run, setRun] = useState<PayrollRun | null>(null);
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Modals
  const [isBonusModalOpen, setIsBonusModalOpen] = useState(false);
  const [isPayModalOpen, setIsPayModalOpen] = useState(false);
  const [isPostGlModalOpen, setIsPostGlModalOpen] = useState(false);
  const [selectedPayslip, setSelectedPayslip] = useState<Payslip | null>(null);
  const [isVoucherModalOpen, setIsVoucherModalOpen] = useState(false);
  const [paymentRefInput, setPaymentRefInput] = useState("");
  const [glPaymentMethod, setGlPaymentMethod] = useState("bank_transfer");

  // Bonus Form
  const bonusForm = useForm<ApplyBonusFormData>({
    resolver: zodResolver(applyBonusSchema),
    defaultValues: {
      bonus_title: "Eid-ul-Fitr Festival Bonus",
      bonus_type: "percentage",
      percentage_of_basic: 50,
      fixed_amount: 0,
      staff_type: "",
    },
  });

  const fetchData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [runData, slipsRes] = await Promise.all([
        payrollApi.getPayrollRunDetail(id),
        payrollApi.getPayslips({ payroll_run: id }),
      ]);
      setRun(runData);
      setPayslips(slipsRes.results || []);
    } catch {
      setNotification({
        type: "error",
        message: t("payroll.loadRunDetailFailed", "Failed to load payroll workspace details."),
      });
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // Lifecycle action handlers
  const handleReview = async () => {
    if (!id) return;
    try {
      const updated = await payrollApi.reviewRun(id);
      setRun(updated);
      setNotification({ type: "success", message: t("payroll.runReviewedSuccess", "Payroll run marked as Reviewed.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.runReviewFailed", "Failed to review payroll run.") });
    }
  };

  const handleApprove = async () => {
    if (!id) return;
    try {
      const updated = await payrollApi.approveRun(id);
      setRun(updated);
      setNotification({ type: "success", message: t("payroll.runApprovedSuccess", "Payroll run approved for disbursement.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.runApproveFailed", "Failed to approve payroll run.") });
    }
  };

  const handleMarkPaidSubmit = async () => {
    if (!id) return;
    try {
      const updated = await payrollApi.markRunPaid(id, paymentRefInput);
      setRun(updated);
      setIsPayModalOpen(false);
      setNotification({ type: "success", message: t("payroll.runPaidSuccess", "Payroll marked as Paid and disbursed.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.runPayFailed", "Failed to mark payroll as paid.") });
    }
  };

  const handleLock = async () => {
    if (!id) return;
    try {
      const updated = await payrollApi.lockRun(id);
      setRun(updated);
      setNotification({ type: "success", message: t("payroll.runLockedSuccess", "Payroll period locked permanently.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.runLockFailed", "Failed to lock payroll run.") });
    }
  };

  const handlePostGlSubmit = async () => {
    if (!id) return;
    try {
      const glRes = await payrollApi.postRunToAccounting(id, glPaymentMethod);
      setIsPostGlModalOpen(false);
      setNotification({
        type: "success",
        message: `${t("payroll.glPostedSuccess", "General Ledger Journal Entry created")}: ${glRes.voucher_no}`,
      });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.glPostFailed", "Failed to post payroll to accounting.") });
    }
  };

  const handleApplyBonusSubmit = async (data: ApplyBonusFormData) => {
    if (!id) return;
    try {
      await payrollApi.applyBonus(id, {
        bonus_title: data.bonus_title,
        percentage_of_basic:
          data.bonus_type === "percentage" && data.percentage_of_basic !== undefined
            ? data.percentage_of_basic.toString()
            : undefined,
        fixed_amount:
          data.bonus_type === "fixed" && data.fixed_amount !== undefined
            ? data.fixed_amount.toString()
            : undefined,
        staff_type: data.staff_type || undefined,
      });
      setIsBonusModalOpen(false);
      setNotification({ type: "success", message: t("payroll.bonusAppliedSuccess", "Festival bonus applied successfully.") });
      void fetchData();
    } catch {
      setNotification({ type: "error", message: t("payroll.bonusApplyFailed", "Failed to apply festival bonus.") });
    }
  };

  const openVoucherModal = (slip: Payslip) => {
    setSelectedPayslip(slip);
    setIsVoucherModalOpen(true);
  };

  if (loading && !run) {
    return <div className="p-8 text-center text-slate-500">{t("common.loading", "Loading workspace...")}</div>;
  }

  if (!run) {
    return (
      <div className="p-8 text-center text-slate-500">
        <p>{t("payroll.runNotFound", "Payroll run not found.")}</p>
        <Button onClick={() => { void navigate("/payroll/runs"); }} className="mt-4">
          {t("common.back", "Back to Runs")}
        </Button>
      </div>
    );
  }

  const monthLabel = isBn
    ? `${MONTH_NAMES_BN[run.month]} ${run.year}`
    : `${MONTH_NAMES_EN[run.month]} ${run.year}`;

  const watchedBonusType = bonusForm.watch("bonus_type");

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { void navigate("/payroll/runs"); }}
            className="gap-1 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("common.back", "Payroll Runs")}
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                {run.title || monthLabel}
              </h1>
              {run.is_locked ? (
                <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                  <Lock className="h-3 w-3" /> Locked
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 capitalize">
                  {run.status}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {monthLabel} • {run.working_days_in_month} {t("payroll.workingDays", "Working Days")} •{" "}
              {t("payroll.deductionBasis", "Deduction Basis")}: {run.absence_deduction_basis.toUpperCase()}
            </p>
          </div>
        </div>

        {/* Action Controls for Lifecycle */}
        <div className="flex flex-wrap items-center gap-2">
          {/* BEFTN Bank Advice Export */}
          <a
            href={payrollApi.getBankAdviceUrl(run.id, "xlsx")}
            download
            className={cn(
              buttonVariants({ variant: "outline" }),
              "gap-1.5 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
            )}
          >
            <Download className="h-4 w-4" />
            {t("payroll.bankAdviceXlsx", "BEFTN Advice (Excel)")}
          </a>

          {/* DRAFT Actions */}
          {run.status === "draft" && !run.is_locked && (
            <>
              <Button
                variant="outline"
                onClick={() => setIsBonusModalOpen(true)}
                className="gap-1.5 text-xs text-amber-700 border-amber-200 hover:bg-amber-50 dark:hover:bg-amber-950/30"
              >
                <Gift className="h-4 w-4" />
                {t("payroll.festivalBonusBtn", "Festival Bonus")}
              </Button>
              <Button
                onClick={() => { void handleReview(); }}
                className="gap-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Clock className="h-4 w-4" />
                {t("payroll.markReviewed", "Mark Reviewed")}
              </Button>
            </>
          )}

          {/* REVIEWED Actions */}
          {run.status === "reviewed" && !run.is_locked && (
            <Button
              onClick={() => { void handleApprove(); }}
              className="gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <CheckCircle2 className="h-4 w-4" />
              {t("payroll.approveForDisbursement", "Approve Run")}
            </Button>
          )}

          {/* APPROVED Actions */}
          {run.status === "approved" && !run.is_locked && (
            <Button
              onClick={() => setIsPayModalOpen(true)}
              className="gap-1.5 text-xs bg-emerald-700 hover:bg-emerald-800 text-white"
            >
              <Send className="h-4 w-4" />
              {t("payroll.disburseSalary", "Mark Disbursed / Paid")}
            </Button>
          )}

          {/* PAID Actions */}
          {run.status === "paid" && (
            <>
              {!run.journal_entry && (
                <Button
                  variant="outline"
                  onClick={() => setIsPostGlModalOpen(true)}
                  className="gap-1.5 text-xs text-indigo-700 border-indigo-200 hover:bg-indigo-50 dark:hover:bg-indigo-950/30"
                >
                  <Building className="h-4 w-4" />
                  {t("payroll.postToGl", "Post to Accounting GL")}
                </Button>
              )}
              {!run.is_locked && (
                <Button
                  variant="outline"
                  onClick={() => { void handleLock(); }}
                  className="gap-1.5 text-xs text-slate-700 border-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <Lock className="h-4 w-4" />
                  {t("payroll.lockPeriod", "Lock Period")}
                </Button>
              )}
            </>
          )}
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

      {/* KPI Overview Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">
            {t("payroll.totalGross", "Total Gross Earnings")}
          </span>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100 mt-1">
            ৳{Number(run.total_gross).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-400 mt-1">Base + allowances + bonuses</p>
        </div>

        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">
            {t("payroll.totalDeductions", "Total Deductions")}
          </span>
          <div className="text-xl font-bold font-mono text-rose-600 mt-1">
            ৳{Number(run.total_deductions).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-400 mt-1">Absence + loan recovery + PF</p>
        </div>

        <div className="p-4 border rounded-xl bg-emerald-50/30 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800 shadow-sm">
          <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 uppercase">
            {t("payroll.netDisbursed", "Net Payout")}
          </span>
          <div className="text-2xl font-black font-mono text-emerald-700 dark:text-emerald-400 mt-1">
            ৳{Number(run.total_net_pay).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-emerald-600 mt-1">Across {run.payslips_count} staff payslips</p>
        </div>

        <div className="p-4 border rounded-xl bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs font-semibold text-slate-500 uppercase">
            {t("payroll.accountingStatus", "Accounting Voucher")}
          </span>
          <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100 mt-1">
            {run.journal_entry_voucher_no || <span className="text-slate-400">Unposted</span>}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {run.journal_entry ? "Integrated into GL Day Book" : "Pending post to accounts"}
          </p>
        </div>
      </div>

      {/* Staff Payslips Broadsheet Table */}
      <div className="border rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="p-4 border-b bg-slate-50/50 dark:bg-slate-800/40 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
            <h2 className="font-bold text-base text-slate-900 dark:text-slate-100">
              {t("payroll.broadsheetTitle", "Staff Salary Broadsheet")} ({payslips.length})
            </h2>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">{t("staff.employeeId", "Staff ID")}</th>
                <th className="py-3 px-4">{t("common.name", "Employee Name")}</th>
                <th className="py-3 px-4">{t("payroll.attendance", "Attendance (P / A)")}</th>
                <th className="py-3 px-4">{t("payroll.basicSalary", "Basic (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.bonus", "Bonus (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.grossEarnings", "Gross (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.absenceDeduction", "Absence Ded.")}</th>
                <th className="py-3 px-4">{t("payroll.loanDeduction", "Loan Ded.")}</th>
                <th className="py-3 px-4">{t("payroll.netPayable", "Net Payable (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.paymentMode", "Channel")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {payslips.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-8 text-center text-slate-500">
                    {t("payroll.noSlipsFound", "No payslips generated for this run.")}
                  </td>
                </tr>
              ) : (
                payslips.map((slip) => (
                  <tr key={slip.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-mono font-semibold text-xs text-slate-700 dark:text-slate-300">
                      {slip.staff_employee_id}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-900 dark:text-slate-100">
                        {slip.staff_name_en}
                      </div>
                      {slip.staff_name_bn && (
                        <div className="text-xs text-slate-500">{slip.staff_name_bn}</div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono">
                      <span className="text-emerald-600 font-semibold">{slip.present_days}d</span> /{" "}
                      <span className="text-rose-600 font-semibold">{slip.absent_days}d</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs">
                      ৳{Number(slip.basic_salary).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-emerald-600">
                      {Number(slip.bonus_amount) > 0 ? (
                        `৳${Number(slip.bonus_amount).toLocaleString()}`
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs font-semibold">
                      ৳{Number(slip.gross_earnings).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-rose-600">
                      {Number(slip.absence_deduction_amount) > 0 ? (
                        `-৳${Number(slip.absence_deduction_amount).toLocaleString()}`
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-rose-600">
                      {Number(slip.loan_deduction_amount) > 0 ? (
                        `-৳${Number(slip.loan_deduction_amount).toLocaleString()}`
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-xs text-emerald-700 dark:text-emerald-400">
                      ৳{Number(slip.net_payable).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-xs capitalize text-slate-600 dark:text-slate-300">
                      {slip.payment_method.replace("_", " ")}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openVoucherModal(slip)}
                        className="h-8 gap-1 text-xs text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        {t("payroll.viewVoucher", "Payslip")}
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal 1: Apply Festival Bonus */}
      <Dialog open={isBonusModalOpen} onOpenChange={setIsBonusModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2 text-amber-700">
              <Gift className="h-5 w-5" />
              {t("payroll.applyBonusTitle", "Apply Eid / Festival Bonus")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              void bonusForm.handleSubmit(handleApplyBonusSubmit)(e);
            }}
            className="space-y-4"
          >
            <FormField>
              <FormLabel>{t("payroll.bonusTitleLabel", "Bonus Title")}</FormLabel>
              <Input placeholder="e.g. Eid-ul-Fitr Bonus" {...bonusForm.register("bonus_title")} />
            </FormField>

            <FormField>
              <FormLabel>{t("payroll.bonusCalculationMode", "Bonus Calculation Mode")}</FormLabel>
              <select
                {...bonusForm.register("bonus_type")}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="percentage">% of Basic Salary (e.g. 50% or 100%)</option>
                <option value="fixed">Fixed BDT Amount (নির্দিষ্ট টাকা)</option>
              </select>
            </FormField>

            {watchedBonusType === "percentage" ? (
              <FormField>
                <FormLabel>{t("payroll.percentageOfBasic", "Percentage of Basic (%)")}</FormLabel>
                <Input
                  type="number"
                  {...bonusForm.register("percentage_of_basic", { valueAsNumber: true })}
                />
              </FormField>
            ) : (
              <FormField>
                <FormLabel>{t("payroll.fixedAmount", "Fixed BDT Amount (৳)")}</FormLabel>
                <Input
                  type="number"
                  {...bonusForm.register("fixed_amount", { valueAsNumber: true })}
                />
              </FormField>
            )}

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsBonusModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" className="bg-amber-600 hover:bg-amber-700 text-white">
                {t("payroll.applyBonusAction", "Apply Bonus to Sheet")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal 2: Mark Paid / Disburse */}
      <Dialog open={isPayModalOpen} onOpenChange={setIsPayModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2 text-emerald-800 dark:text-emerald-400">
              <Wallet className="h-5 w-5" />
              {t("payroll.disburseSalaryTitle", "Confirm Salary Disbursement")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              This action marks all payslips in <strong>{monthLabel}</strong> as PAID and settles active staff loan installments.
            </p>
            <FormField>
              <FormLabel>{t("payroll.paymentReference", "Payment / BEFTN Batch Reference")}</FormLabel>
              <Input
                placeholder="e.g. BEFTN-2026-07-001 or Cheque #98421"
                value={paymentRefInput}
                onChange={(e) => setPaymentRefInput(e.target.value)}
              />
            </FormField>
          </div>
          <DialogFooter className="pt-2">
            <Button variant="outline" onClick={() => setIsPayModalOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              onClick={() => { void handleMarkPaidSubmit(); }}
              className="bg-emerald-700 hover:bg-emerald-800 text-white"
            >
              {t("payroll.confirmDisburse", "Confirm Disbursement")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal 3: Post to Accounting GL */}
      <Dialog open={isPostGlModalOpen} onOpenChange={setIsPostGlModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2 text-indigo-700">
              <Building className="h-5 w-5" />
              {t("payroll.postToGlTitle", "Post Payroll to General Ledger")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Creates a double-entry Journal Voucher in the institutional Day Book:
              <br />
              • <strong>Debit</strong>: Salary & Benefits Expense (৳{Number(run.total_gross).toLocaleString()})
              <br />
              • <strong>Credit</strong>: Bank / Cash Disbursed (৳{Number(run.total_net_pay).toLocaleString()}) & PF Payable
            </p>
            <FormField>
              <FormLabel>{t("payroll.postingAccount", "Credit Disbursement Account")}</FormLabel>
              <select
                value={glPaymentMethod}
                onChange={(e) => setGlPaymentMethod(e.target.value)}
                className="w-full h-10 px-3 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              >
                <option value="bank_transfer">School Main Bank Account (BEFTN)</option>
                <option value="cash">Institutional Cash in Hand</option>
                <option value="cheque">Bank Cheque</option>
              </select>
            </FormField>
          </div>
          <DialogFooter className="pt-2">
            <Button variant="outline" onClick={() => setIsPostGlModalOpen(false)}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              onClick={() => { void handlePostGlSubmit(); }}
              className="bg-indigo-700 hover:bg-indigo-800 text-white"
            >
              {t("payroll.createVoucher", "Create Journal Voucher")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payslip Voucher Modal */}
      <PayslipVoucherModal
        payslip={selectedPayslip}
        isOpen={isVoucherModalOpen}
        onClose={() => setIsVoucherModalOpen(false)}
        pdfUrl={selectedPayslip ? payrollApi.getPayslipPdfUrl(selectedPayslip.id) : undefined}
      />
    </div>
  );
}
