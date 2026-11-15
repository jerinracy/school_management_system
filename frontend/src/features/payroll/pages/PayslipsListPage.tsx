import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  FileText,
  Search,
  Eye,
  CheckCircle2,
  Clock,
  Landmark,
  Smartphone,
  Building,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  payrollApi,
  type Payslip,
} from "@/features/payroll/api/payrollApi";
import { PayslipVoucherModal } from "../components/PayslipVoucherModal";

const MONTH_NAMES_EN = [
  "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

const MONTH_NAMES_BN = [
  "", "জানু", "ফেব্রু", "মার্চ", "এপ্রিল", "মে", "জুন",
  "জুলাই", "আগস্ট", "সেপ্টে", "অক্টো", "নভে", "ডিসে"
];

export default function PayslipsListPage() {
  const { t, i18n } = useTranslation();
  const isBn = i18n.language === "bn";

  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [paidFilter, setPaidFilter] = useState<string>("all");
  const [selectedSlip, setSelectedSlip] = useState<Payslip | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchPayslips = useCallback(async () => {
    setLoading(true);
    try {
      const isPaid = paidFilter === "all" ? undefined : paidFilter === "paid";
      const res = await payrollApi.getPayslips({
        is_paid: isPaid,
        search: search || undefined,
      });
      setPayslips(res.results || []);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [paidFilter, search]);

  useEffect(() => {
    void fetchPayslips();
  }, [fetchPayslips]);

  const openSlipVoucher = (slip: Payslip) => {
    setSelectedSlip(slip);
    setIsModalOpen(true);
  };

  const filteredSlips = payslips.filter(
    (s) =>
      s.staff_employee_id.toLowerCase().includes(search.toLowerCase()) ||
      s.staff_name_en.toLowerCase().includes(search.toLowerCase()) ||
      (s.staff_name_bn && s.staff_name_bn.includes(search))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <FileText className="h-6 w-6 text-emerald-600" />
          {t("payroll.payslipsTitle", "Staff Payslips Archive")}
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t(
            "payroll.payslipsSubtitle",
            "Browse, inspect, and reprint bilingual salary slips and download official WeasyPrint PDF vouchers."
          )}
        </p>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("common.search", "Search employee ID, name...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
            <span>{t("common.status", "Disbursement Status")}:</span>
            <select
              value={paidFilter}
              onChange={(e) => setPaidFilter(e.target.value)}
              className="h-9 px-2 rounded-md border text-sm bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
            >
              <option value="all">All Payslips</option>
              <option value="paid">Paid / Disbursed</option>
              <option value="unpaid">Pending Disbursement</option>
            </select>
          </label>
        </div>
      </div>

      {/* Payslips Table */}
      <div className="border rounded-xl bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">{t("payroll.period", "Month/Year")}</th>
                <th className="py-3 px-4">{t("staff.employeeId", "Staff ID")}</th>
                <th className="py-3 px-4">{t("common.name", "Employee Name")}</th>
                <th className="py-3 px-4">{t("payroll.basicSalary", "Basic (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.grossAmount", "Gross (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.deductions", "Deductions (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.netPayout", "Net Payable (৳)")}</th>
                <th className="py-3 px-4">{t("payroll.paymentMode", "Channel")}</th>
                <th className="py-3 px-4">{t("common.status", "Status")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading payslips...")}
                  </td>
                </tr>
              ) : filteredSlips.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    {t("payroll.noSlipsFound", "No payslips matching filter criteria.")}
                  </td>
                </tr>
              ) : (
                filteredSlips.map((slip) => (
                  <tr key={slip.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-bold text-xs text-slate-900 dark:text-slate-100">
                      {isBn ? `${MONTH_NAMES_BN[slip.month]} ${slip.year}` : `${MONTH_NAMES_EN[slip.month]} ${slip.year}`}
                    </td>
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
                    <td className="py-3 px-4 font-mono text-xs">
                      ৳{Number(slip.basic_salary).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs font-semibold">
                      ৳{Number(slip.gross_earnings).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-rose-600">
                      ৳{Number(slip.total_deductions).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-xs text-emerald-700 dark:text-emerald-400">
                      ৳{Number(slip.net_payable).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      <span className="inline-flex items-center gap-1 capitalize font-medium text-slate-600 dark:text-slate-300">
                        {slip.payment_method === "bank_transfer" ? (
                          <>
                            <Landmark className="h-3 w-3 text-blue-600" /> Bank
                          </>
                        ) : slip.payment_method === "mfs" ? (
                          <>
                            <Smartphone className="h-3 w-3 text-rose-600" /> MFS
                          </>
                        ) : (
                          <>
                            <Building className="h-3 w-3 text-slate-500" /> Cash
                          </>
                        )}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {slip.is_paid ? (
                        <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          <CheckCircle2 className="h-3 w-3" /> Paid
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                          <Clock className="h-3 w-3" /> Pending
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openSlipVoucher(slip)}
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

      {/* Printable Voucher Modal */}
      <PayslipVoucherModal
        payslip={selectedSlip}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        pdfUrl={selectedSlip ? payrollApi.getPayslipPdfUrl(selectedSlip.id) : undefined}
      />
    </div>
  );
}
