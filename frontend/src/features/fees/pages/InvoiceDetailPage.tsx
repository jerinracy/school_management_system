import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  CreditCard,
  Ban,
  Calendar,
  User,
  Printer,
  DollarSign,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { feesApi, type InvoiceItem } from "@/features/fees/api/feesApi";

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState<InvoiceItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [isCancelling, setIsCancelling] = useState(false);

  const fetchInvoice = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await feesApi.getInvoice(id);
      setInvoice(data as InvoiceItem);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchInvoice();
  }, [fetchInvoice]);

  const handleCancel = async () => {
    if (!id || !cancelReason.trim()) return;
    setIsCancelling(true);
    try {
      await feesApi.cancelInvoice(id, cancelReason);
      setIsCancelModalOpen(false);
      void fetchInvoice();
    } catch {
      // handled
    } finally {
      setIsCancelling(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-slate-500">{t("common.loading", "Loading invoice...")}</div>;
  }

  if (!invoice) {
    return (
      <div className="p-12 text-center">
        <p className="text-slate-500">{t("fees.invoiceNotFound", "Invoice not found.")}</p>
        <Link to="/fees/invoices">
          <Button variant="outline" className="mt-4">
            {t("common.back", "Back to Invoices")}
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Bar */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <Link to="/fees/invoices">
            <Button variant="outline" size="icon" aria-label={t("common.back", "Back")}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              {t("fees.invoiceNo", "Invoice")} #{invoice.invoice_number}
            </h1>
            <p className="text-xs text-slate-500">
              {invoice.session_name} • {invoice.title || invoice.invoice_type}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {Number(invoice.due_amount) > 0 && invoice.status !== "cancelled" && (
            <Button
              onClick={() => { void navigate(`/fees/collect?student_id=${invoice.student}&invoice_id=${invoice.id}`); }}
              className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
            >
              <CreditCard className="h-4 w-4" />
              {t("fees.collectFee", "Collect Payment")}
            </Button>
          )}

          <Button variant="outline" onClick={() => window.print()} className="gap-2">
            <Printer className="h-4 w-4" />
            {t("common.print", "Print")}
          </Button>

          {invoice.status !== "cancelled" && invoice.status !== "paid" && (
            <Button variant="outline" onClick={() => setIsCancelModalOpen(true)} className="gap-2 text-rose-600 hover:text-rose-700">
              <Ban className="h-4 w-4" />
              {t("fees.cancelInvoice", "Cancel")}
            </Button>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
            <User className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block">{t("students.student", "Student Name")}</span>
            <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">{invoice.student_name}</span>
            <span className="font-mono text-xs text-slate-400 block">{invoice.student_code}</span>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block">{t("fees.dates", "Timeline")}</span>
            <span className="text-xs text-slate-700 dark:text-slate-300 block">
              {t("fees.issueDate", "Issued")}: <strong>{invoice.issue_date || "—"}</strong>
            </span>
            <span className="text-xs text-rose-600 dark:text-rose-400 block">
              {t("fees.dueDate", "Due")}: <strong>{invoice.due_date || "—"}</strong>
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
            <DollarSign className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block">{t("fees.netDue", "Net Due Balance")}</span>
            <span className="text-xl font-bold font-mono text-rose-600 dark:text-rose-400">
              ৳{Number(invoice.due_amount).toFixed(2)}
            </span>
            <span className="text-[11px] text-slate-400 block">
              Total: ৳{Number(invoice.total_payable).toFixed(2)} | Paid: ৳{Number(invoice.paid_amount).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
            {t("fees.lineItems", "Bill Line Items & Breakdowns")}
          </h3>
        </div>
        <table className="w-full text-sm text-left border-collapse">
          <thead className="bg-slate-50/50 dark:bg-slate-800/20 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
            <tr>
              <th className="py-3 px-4">{t("fees.feeHead", "Fee Head")}</th>
              <th className="py-3 px-4 text-right">{t("fees.baseAmount", "Base (৳)")}</th>
              <th className="py-3 px-4 text-right">{t("fees.waiver", "Waiver (৳)")}</th>
              <th className="py-3 px-4 text-right">{t("fees.fine", "Fine (৳)")}</th>
              <th className="py-3 px-4 text-right">{t("fees.payable", "Payable (৳)")}</th>
              <th className="py-3 px-4 text-right">{t("fees.paid", "Paid (৳)")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {(invoice.lines || []).length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-400 text-xs italic">
                  {t("fees.noLineItems", "No line items found for this invoice.")}
                </td>
              </tr>
            ) : (
              invoice.lines?.map((line) => (
                <tr key={line.id}>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-800 dark:text-slate-200 block">{line.fee_head_name}</span>
                    <span className="font-mono text-xs text-slate-400">{line.fee_head_code}</span>
                  </td>
                  <td className="py-3 px-4 text-right font-mono">৳{Number(line.amount).toFixed(2)}</td>
                  <td className="py-3 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400">
                    -৳{Number(line.waiver_amount).toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-rose-600 dark:text-rose-400">
                    +৳{Number(line.fine_amount).toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-slate-100">
                    ৳{Number(line.payable_amount).toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-emerald-700 dark:text-emerald-400 font-semibold">
                    ৳{Number(line.paid_amount).toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
          <tfoot className="border-t-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 text-xs font-bold">
            <tr>
              <td className="py-3 px-4 uppercase">{t("fees.netSummary", "Net Summary")}</td>
              <td className="py-3 px-4 text-right font-mono">৳{Number(invoice.subtotal_amount).toFixed(2)}</td>
              <td className="py-3 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400">
                -৳{Number(invoice.waiver_amount).toFixed(2)}
              </td>
              <td className="py-3 px-4 text-right font-mono text-rose-600 dark:text-rose-400">
                +৳{Number(invoice.fine_amount).toFixed(2)}
              </td>
              <td className="py-3 px-4 text-right font-mono text-slate-900 dark:text-slate-100 text-sm">
                ৳{Number(invoice.total_payable).toFixed(2)}
              </td>
              <td className="py-3 px-4 text-right font-mono text-emerald-700 dark:text-emerald-400 text-sm">
                ৳{Number(invoice.paid_amount).toFixed(2)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Cancel Modal */}
      <Dialog open={isCancelModalOpen} onOpenChange={setIsCancelModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("fees.cancelInvoiceTitle", "Cancel Invoice")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-xs text-slate-500">
              {t("fees.cancelInvoiceWarning", "Cancelling will void any pending dues on this invoice. Please provide a formal justification.")}
            </p>
            <Input
              placeholder={t("fees.cancellationReason", "Reason for cancellation...")}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCancelModalOpen(false)}>
              {t("common.back", "Back")}
            </Button>
            <Button
              onClick={() => { void handleCancel(); }}
              disabled={isCancelling || !cancelReason.trim()}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              {isCancelling ? t("common.cancelling", "Cancelling...") : t("fees.confirmCancel", "Confirm Void")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
