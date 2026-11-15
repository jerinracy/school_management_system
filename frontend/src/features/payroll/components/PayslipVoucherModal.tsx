import React, { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Printer, Download, Building, CheckCircle2, X } from "lucide-react";
import type { Payslip } from "../api/payrollApi";

interface PayslipVoucherModalProps {
  payslip: Payslip | null;
  isOpen: boolean;
  onClose: () => void;
  pdfUrl?: string;
}

const MONTH_NAMES_EN = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const MONTH_NAMES_BN = [
  "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
  "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"
];

export const PayslipVoucherModal: React.FC<PayslipVoucherModalProps> = ({
  payslip,
  isOpen,
  onClose,
  pdfUrl,
}) => {
  const { t, i18n } = useTranslation();
  const printRef = useRef<HTMLDivElement>(null);
  const isBn = i18n.language === "bn";

  if (!payslip) return null;

  const handlePrint = () => {
    window.print();
  };

  const monthLabel = isBn
    ? `${MONTH_NAMES_BN[payslip.month]} ${payslip.year}`
    : `${MONTH_NAMES_EN[payslip.month]} ${payslip.year}`;

  const earningsLines = payslip.lines.filter((l) => l.line_type === "earning");
  const deductionLines = payslip.lines.filter((l) => l.line_type === "deduction");

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl overflow-y-auto max-h-[90vh]">
        <DialogHeader className="flex flex-row items-center justify-between border-b pb-3">
          <DialogTitle className="text-xl font-bold flex items-center gap-2 text-emerald-800 dark:text-emerald-400">
            <Building className="h-5 w-5" />
            {t("payroll.payslipVoucher", "Salary Payslip Voucher")}
          </DialogTitle>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 hover:text-slate-600 focus:outline-none"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </DialogHeader>

        {/* Printable Voucher Section */}
        <div ref={printRef} className="p-4 bg-white dark:bg-slate-900 border rounded-lg shadow-sm text-slate-900 dark:text-slate-100">
          {/* Institution Header */}
          <div className="text-center border-b pb-4 mb-4">
            <h2 className="text-2xl font-black text-emerald-800 dark:text-emerald-400 tracking-wide">
              {isBn ? "উত্তরা মডেল হাই স্কুল ও কলেজ" : "Uttara Model High School & College"}
            </h2>
            <p className="text-xs text-slate-500 font-medium mt-1">
              {isBn ? "ইআইআইএন: ১৩৪৫৮২ | ঢাকা শিক্ষা বোর্ড | সেক্টর-৪, উত্তরা, ঢাকা" : "EIIN: 134582 | Dhaka Education Board | Sector-4, Uttara, Dhaka-1230"}
            </p>
            <div className="inline-block mt-2 px-3 py-0.5 bg-emerald-100 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 rounded font-semibold text-xs tracking-wider uppercase">
              {t("payroll.monthlySalarySlip", "Monthly Salary Payslip")} — {monthLabel}
            </div>
          </div>

          {/* Employee & Attendance Overview Grid */}
          <div className="grid grid-cols-2 gap-4 text-xs bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border mb-4">
            <div>
              <p className="font-semibold text-slate-500 uppercase tracking-wider">{t("payroll.employeeDetails", "Employee Details")}</p>
              <p className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1">
                {isBn && payslip.staff_name_bn ? payslip.staff_name_bn : payslip.staff_name_en}
              </p>
              <p className="text-slate-600 dark:text-slate-300 font-mono">
                ID: {payslip.staff_employee_id}
              </p>
              <p className="text-slate-600 dark:text-slate-300 capitalize">
                {t("payroll.paymentMode", "Payment Mode")}: {payslip.payment_method.replace("_", " ")}
              </p>
            </div>
            <div>
              <p className="font-semibold text-slate-500 uppercase tracking-wider">{t("payroll.attendanceSummary", "Attendance Summary")}</p>
              <div className="grid grid-cols-2 gap-1 mt-1 text-slate-700 dark:text-slate-300">
                <span>{t("payroll.workingDays", "Working Days")}:</span>
                <span className="font-semibold font-mono">{payslip.working_days}</span>
                <span>{t("payroll.presentDays", "Present")}:</span>
                <span className="font-semibold font-mono text-emerald-600">{payslip.present_days}</span>
                <span>{t("payroll.leaveDays", "Paid Leave")}:</span>
                <span className="font-semibold font-mono">{payslip.paid_leave_days}</span>
                <span>{t("payroll.absentDays", "Absent")}:</span>
                <span className="font-semibold font-mono text-rose-600">{payslip.absent_days}</span>
              </div>
            </div>
          </div>

          {/* Two-Column Breakdown: Earnings vs Deductions */}
          <div className="grid grid-cols-2 gap-6 text-sm">
            {/* Earnings Column */}
            <div className="border rounded-md p-3 bg-emerald-50/30 dark:bg-emerald-950/20">
              <div className="font-bold text-emerald-800 dark:text-emerald-300 border-b pb-1 mb-2 flex justify-between">
                <span>{t("payroll.earnings", "Earnings")}</span>
                <span>BDT (৳)</span>
              </div>
              <div className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                <div className="flex justify-between">
                  <span>{t("payroll.basicSalary", "Basic Salary")}</span>
                  <span className="font-mono">৳{Number(payslip.basic_salary).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                </div>
                {earningsLines.map((line) => (
                  <div key={line.id} className="flex justify-between">
                    <span>{isBn && line.name_bn ? line.name_bn : line.name_en}</span>
                    <span className="font-mono">৳{Number(line.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                ))}
                {Number(payslip.bonus_amount) > 0 && (
                  <div className="flex justify-between text-emerald-700 dark:text-emerald-400 font-medium">
                    <span>{t("payroll.festivalBonus", "Festival Bonus")}</span>
                    <span className="font-mono">৳{Number(payslip.bonus_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                )}
                {Number(payslip.overtime_amount) > 0 && (
                  <div className="flex justify-between">
                    <span>{t("payroll.overtimeAmount", "Overtime")}</span>
                    <span className="font-mono">৳{Number(payslip.overtime_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                )}
              </div>
              <div className="border-t mt-3 pt-2 font-bold text-slate-900 dark:text-slate-100 flex justify-between">
                <span>{t("payroll.totalGross", "Gross Earnings")}</span>
                <span className="font-mono text-emerald-700 dark:text-emerald-400">
                  ৳{Number(payslip.gross_earnings).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            {/* Deductions Column */}
            <div className="border rounded-md p-3 bg-rose-50/30 dark:bg-rose-950/20">
              <div className="font-bold text-rose-800 dark:text-rose-300 border-b pb-1 mb-2 flex justify-between">
                <span>{t("payroll.deductions", "Deductions")}</span>
                <span>BDT (৳)</span>
              </div>
              <div className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                {Number(payslip.absence_deduction_amount) > 0 && (
                  <div className="flex justify-between text-rose-600">
                    <span>{t("payroll.absenceDeduction", "Absence Deduction")}</span>
                    <span className="font-mono">৳{Number(payslip.absence_deduction_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                )}
                {Number(payslip.pf_employee_amount) > 0 && (
                  <div className="flex justify-between">
                    <span>{t("payroll.providentFund", "Provident Fund (PF)")}</span>
                    <span className="font-mono">৳{Number(payslip.pf_employee_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                )}
                {Number(payslip.loan_deduction_amount) > 0 && (
                  <div className="flex justify-between">
                    <span>{t("payroll.loanInstallment", "Loan / Advance Installment")}</span>
                    <span className="font-mono">৳{Number(payslip.loan_deduction_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                )}
                {deductionLines.map((line) => (
                  <div key={line.id} className="flex justify-between">
                    <span>{isBn && line.name_bn ? line.name_bn : line.name_en}</span>
                    <span className="font-mono">৳{Number(line.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  </div>
                ))}
              </div>
              <div className="border-t mt-3 pt-2 font-bold text-slate-900 dark:text-slate-100 flex justify-between">
                <span>{t("payroll.totalDeductions", "Total Deductions")}</span>
                <span className="font-mono text-rose-600">
                  ৳{Number(payslip.total_deductions).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>

          {/* Net Payable Highlight Banner */}
          <div className="mt-4 p-3 bg-emerald-700 text-white rounded-lg flex items-center justify-between shadow-sm">
            <div>
              <p className="text-xs uppercase tracking-wider font-semibold opacity-90">
                {t("payroll.netPayableSalary", "Net Disbursed Amount")}
              </p>
              <p className="text-xs opacity-80 mt-0.5">
                {payslip.is_paid ? (
                  <span className="flex items-center gap-1 font-medium">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {t("payroll.paidOn", "Disbursed")} {payslip.paid_at ? new Date(payslip.paid_at).toLocaleDateString() : ""}
                  </span>
                ) : (
                  t("payroll.pendingApproval", "Pending Disbursement")
                )}
              </p>
            </div>
            <div className="text-right">
              <span className="text-2xl font-black font-mono">
                ৳{Number(payslip.net_payable).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          {/* Signatures */}
          <div className="grid grid-cols-3 gap-8 mt-12 text-center text-xs text-slate-500 border-t pt-8">
            <div>
              <div className="border-b border-dashed border-slate-400 mb-1 w-3/4 mx-auto" />
              <span>{t("payroll.preparedBy", "Prepared By (Accountant)")}</span>
            </div>
            <div>
              <div className="border-b border-dashed border-slate-400 mb-1 w-3/4 mx-auto" />
              <span>{t("payroll.checkedBy", "Approved By (Principal)")}</span>
            </div>
            <div>
              <div className="border-b border-dashed border-slate-400 mb-1 w-3/4 mx-auto" />
              <span>{t("payroll.receiverSign", "Employee Signature")}</span>
            </div>
          </div>
        </div>

        <DialogFooter className="flex justify-between sm:justify-between items-center gap-2 border-t pt-3">
          <Button variant="outline" onClick={onClose}>
            {t("common.close", "Close")}
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handlePrint} className="gap-1.5">
              <Printer className="h-4 w-4" />
              {t("common.print", "Print Voucher")}
            </Button>
            {pdfUrl && (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(buttonVariants(), "gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white")}
              >
                <Download className="h-4 w-4" />
                {t("payroll.downloadPdf", "Official PDF")}
              </a>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
