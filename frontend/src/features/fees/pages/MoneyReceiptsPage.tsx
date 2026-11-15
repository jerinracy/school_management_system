import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Receipt, Search, Printer, CheckCircle, Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { feesApi, type MoneyReceiptItem } from "@/features/fees/api/feesApi";
import { MoneyReceiptPreview, type ReceiptData } from "@/features/fees/components/MoneyReceiptPreview";

export default function MoneyReceiptsPage() {
  const { t } = useTranslation();

  const [receipts, setReceipts] = useState<MoneyReceiptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedReceipt, setSelectedReceipt] = useState<ReceiptData | null>(null);

  const fetchReceipts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await feesApi.getMoneyReceipts({ search: search || undefined });
      setReceipts(((res as { results?: MoneyReceiptItem[] }).results ?? []));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void fetchReceipts();
  }, [fetchReceipts]);

  const handleOpenReceipt = (rec: MoneyReceiptItem) => {
    setSelectedReceipt({
      receipt_number: rec.receipt_number,
      payment_date: rec.issued_at ? rec.issued_at.slice(0, 10) : rec.created_at.slice(0, 10),
      payment_method: "OFFICIAL RECEIPT",
      student_name: rec.student_name_en,
      student_code: rec.student,
      items: [
        {
          head_name: t("fees.feeIntake", "Fee Collection"),
          amount: rec.total_amount,
        },
      ],
      subtotal: rec.total_amount,
      total_paid: rec.total_amount,
      received_by_name: rec.issued_by_name,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Receipt className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t("fees.moneyReceipts", "Money Receipts")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("fees.receiptsSubtitle", "Official 3-copy Bangladeshi money receipt vouchers and collection audit register.")}
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("fees.searchReceiptPrompt", "Search by receipt # or student...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-white dark:bg-slate-900"
          />
        </div>
      </div>

      {/* Receipts Table */}
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
              <tr>
                <th className="py-3 px-4">{t("fees.receiptNo", "Receipt #")}</th>
                <th className="py-3 px-4">{t("students.student", "Student Name")}</th>
                <th className="py-3 px-4">{t("fees.issuedDate", "Issued Date")}</th>
                <th className="py-3 px-4">{t("fees.collector", "Issued By")}</th>
                <th className="py-3 px-4 text-right">{t("common.amount", "Amount (৳)")}</th>
                <th className="py-3 px-4 text-center">{t("common.status", "Status")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading receipts...")}
                  </td>
                </tr>
              ) : receipts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <Receipt className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    {t("fees.noReceiptsFound", "No money receipts issued yet.")}
                  </td>
                </tr>
              ) : (
                receipts.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-900 dark:text-slate-100">
                      {rec.receipt_number}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">
                      {rec.student_name_en}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-500">
                      {rec.issued_at ? rec.issued_at.split("T")[0] : rec.created_at.split("T")[0]}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600 dark:text-slate-400">
                      {rec.issued_by_name || "Cashier"}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      ৳{Number(rec.total_amount).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {rec.is_cancelled ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          <Ban className="h-3 w-3" />
                          {t("fees.statusCancelled", "Cancelled")}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400">
                          <CheckCircle className="h-3 w-3" />
                          {t("fees.statusValid", "Valid")}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenReceipt(rec)}
                        className="h-8 gap-1.5 text-xs text-emerald-700 dark:text-emerald-400"
                      >
                        <Printer className="h-3.5 w-3.5" />
                        {t("common.print", "Print Slip")}
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Printable Receipt Preview Modal */}
      {selectedReceipt && (
        <MoneyReceiptPreview receipt={selectedReceipt} onClose={() => setSelectedReceipt(null)} />
      )}
    </div>
  );
}
