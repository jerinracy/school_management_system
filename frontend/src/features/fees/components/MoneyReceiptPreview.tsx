import { useTranslation } from "react-i18next";
import { Printer, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";
import type { SupportedLanguage } from "@/i18n";

export interface ReceiptData {
  receipt_number: string;
  payment_date: string;
  payment_method: string;
  transaction_id?: string;
  student_name: string;
  student_code: string;
  class_name?: string;
  section_name?: string;
  roll_no?: number | string | null;
  received_by_name?: string | null;
  items: Array<{
    head_name: string;
    amount: string | number;
  }>;
  subtotal: string | number;
  waiver?: string | number;
  fine?: string | number;
  total_paid: string | number;
}

interface MoneyReceiptPreviewProps {
  receipt: ReceiptData;
  onClose: () => void;
}

export function MoneyReceiptPreview({ receipt, onClose }: MoneyReceiptPreviewProps) {
  const { t, i18n } = useTranslation();
  const currentLang: SupportedLanguage = i18n.language === "bn" ? "bn" : "en";
  const { getLocalizedName, getEIIN, getBoard, getLogoUrl } = useBrandingStore();

  const schoolName = getLocalizedName(currentLang);
  const schoolEIIN = getEIIN();
  const schoolBoard = getBoard();
  const schoolLogo = getLogoUrl();

  const handlePrint = () => {
    window.print();
  };

  const copies = [
    { title: t("fees.studentCopy", "Student Copy"), badge: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300" },
    { title: t("fees.officeCopy", "Office Copy"), badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
    { title: t("fees.bankCopy", "Bank Copy"), badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade p-4 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 w-full max-w-4xl max-h-[92vh] rounded-xl shadow-2xl flex flex-col overflow-hidden border border-slate-200 dark:border-slate-800">
        {/* Modal Action Header (Hidden during Print) */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 print:hidden">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-lg">
              {t("fees.receiptPreview", "Money Receipt Voucher")} — #{receipt.receipt_number}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handlePrint} className="bg-primary hover:bg-primary/90 text-white gap-2 shadow-sm">
              <Printer className="h-4 w-4" />
              {t("common.print", "Print Receipt")}
            </Button>
            <Button variant="outline" size="icon" onClick={onClose} aria-label={t("common.close", "Close")}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Printable Receipt Body */}
        <div className="p-6 overflow-y-auto space-y-6 print:p-0 print:space-y-4 print:overflow-visible">
          {copies.map((copy, index) => (
            <div
              key={index}
              className={`p-5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 ${
                index < 2 ? "border-dashed pb-6 print:border-b-2 print:border-dashed" : ""
              }`}
            >
              {/* Slip Header */}
              <div className="flex items-center justify-between border-b pb-3 border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-3">
                  {schoolLogo ? (
                    <img src={schoolLogo} alt="Logo" className="h-10 w-10 object-contain rounded" />
                  ) : null}
                  <div>
                    <h4 className="font-bold text-base leading-tight">{schoolName}</h4>
                    <p className="text-xs text-slate-500">
                      EIIN: {schoolEIIN} | {schoolBoard ? `Board: ${schoolBoard} | ` : ""}{t("fees.moneyReceipt", "Money Receipt")}
                    </p>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end">
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${copy.badge} uppercase tracking-wider`}>
                    {copy.title}
                  </span>
                  <span className="text-xs text-slate-500 mt-1">
                    No: <strong className="font-mono text-slate-900 dark:text-slate-100">{receipt.receipt_number}</strong>
                  </span>
                  <span className="text-[11px] text-slate-400">Date: {receipt.payment_date}</span>
                </div>
              </div>

              {/* Student Metadata Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-3 text-xs bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded">
                <div>
                  <span className="text-slate-500 block">{t("students.name", "Student Name")}:</span>
                  <span className="font-semibold">{receipt.student_name}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">{t("students.studentId", "Student ID")}:</span>
                  <span className="font-mono font-semibold">{receipt.student_code}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">{t("academics.class", "Class")} / {t("academics.section", "Sec")}:</span>
                  <span className="font-medium">
                    {receipt.class_name || "—"} {receipt.section_name ? `(${receipt.section_name})` : ""} {receipt.roll_no ? `| Roll: ${receipt.roll_no}` : ""}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">{t("fees.paymentMethod", "Method")}:</span>
                  <span className="font-semibold uppercase text-emerald-600 dark:text-emerald-400">
                    {receipt.payment_method} {receipt.transaction_id ? `(${receipt.transaction_id})` : ""}
                  </span>
                </div>
              </div>

              {/* Items Table */}
              <table className="w-full text-xs text-left my-2 border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500">
                    <th className="py-1">{t("fees.feeHead", "Fee Description")}</th>
                    <th className="py-1 text-right">{t("common.amount", "Amount (৳)")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                  {receipt.items.map((item, i) => (
                    <tr key={i}>
                      <td className="py-1">{item.head_name}</td>
                      <td className="py-1 text-right font-mono">৳{Number(item.amount).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-slate-300 dark:border-slate-700 font-bold">
                    <td className="py-1.5">{t("fees.totalPaid", "Total Paid (Net)")}</td>
                    <td className="py-1.5 text-right font-mono text-emerald-700 dark:text-emerald-400 text-sm">
                      ৳{Number(receipt.total_paid).toFixed(2)}
                    </td>
                  </tr>
                </tfoot>
              </table>

              {/* Signature Footer */}
              <div className="flex justify-between items-end mt-4 pt-4 text-[11px] text-slate-400">
                <div>
                  <span className="block border-t border-slate-400 dark:border-slate-600 pt-0.5 w-28 text-center text-slate-600 dark:text-slate-300">
                    {t("fees.cashierSign", "Cashier / Collector")}
                  </span>
                </div>
                <div>
                  <span className="block border-t border-slate-400 dark:border-slate-600 pt-0.5 w-28 text-center text-slate-600 dark:text-slate-300">
                    {t("fees.studentSign", "Payer's Signature")}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
