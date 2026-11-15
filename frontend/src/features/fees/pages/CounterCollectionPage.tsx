import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  CreditCard,
  Search,
  User,
  CheckCircle2,
  DollarSign,
  AlertCircle,
  Receipt,
  Smartphone,
  Building,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { feesApi, type InvoiceItem, type PaymentItem } from "@/features/fees/api/feesApi";
import { MoneyReceiptPreview, type ReceiptData } from "@/features/fees/components/MoneyReceiptPreview";
import { apiClient } from "@/lib/api-client";

interface StudentOption {
  id: string;
  student_id: string;
  name_en: string;
  name_bn?: string;
  class_name?: string;
  section_name?: string;
  roll_no?: number | string | null;
}

export default function CounterCollectionPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const paramStudentId = searchParams.get("student_id");
  const paramInvoiceId = searchParams.get("invoice_id");

  const [studentSearch, setStudentSearch] = useState("");
  const [studentResults, setStudentResults] = useState<StudentOption[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<StudentOption | null>(null);
  const [studentInvoices, setStudentInvoices] = useState<InvoiceItem[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(paramInvoiceId || null);
  const [loadingInvoices, setLoadingInvoices] = useState(false);

  // Payment form state
  const [amount, setAmount] = useState<string>("0.00");
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "bkash" | "nagad" | "rocket" | "bank" | "card">("cash");
  const [bankName, setBankName] = useState("");
  const [chequeNo, setChequeNo] = useState("");
  const [transactionId, setTransactionId] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Success receipt modal
  const [generatedReceipt, setGeneratedReceipt] = useState<ReceiptData | null>(null);

  // Search students
  const handleSearchStudents = useCallback(async (query: string) => {
    if (!query || query.length < 2) {
      setStudentResults([]);
      return;
    }
    try {
      const res = await apiClient.GET("/api/v1/students/", {
        params: { query: { search: query } as never },
      });
      if (res.data && "results" in res.data) {
        setStudentResults(res.data.results);
      }
    } catch {
      // ignore
    }
  }, []);

  // Fetch invoices for selected student
  const fetchStudentInvoices = useCallback(async (studentId: string) => {
    setLoadingInvoices(true);
    try {
      const res = await feesApi.getInvoices({ student: studentId });
      const items = ((res as { results?: InvoiceItem[] }).results ?? []);
      // Filter unpaid or partially paid
      const unpaid = items.filter((inv) => inv.status !== "paid" && inv.status !== "cancelled");
      setStudentInvoices(unpaid);

      // Auto-select first unpaid invoice or pre-selected invoice
      if (paramInvoiceId) {
        const found = unpaid.find((i) => i.id === paramInvoiceId);
        if (found) {
          setSelectedInvoiceId(found.id);
          setAmount(Number(found.due_amount).toFixed(2));
          return;
        }
      }

      if (unpaid.length > 0 && unpaid[0]) {
        setSelectedInvoiceId(unpaid[0].id);
        setAmount(Number(unpaid[0].due_amount).toFixed(2));
      } else {
        setSelectedInvoiceId(null);
        setAmount("0.00");
      }
    } catch {
      // ignore
    } finally {
      setLoadingInvoices(false);
    }
  }, [paramInvoiceId]);

  // Load student if student_id is in query params
  useEffect(() => {
    if (paramStudentId) {
      void (async () => {
        try {
          const res = await apiClient.GET("/api/v1/students/{id}/", {
            params: { path: { id: paramStudentId } },
          });
          if (res.data) {
            const st = res.data as unknown as StudentOption;
            setSelectedStudent(st);
            void fetchStudentInvoices(st.id);
          }
        } catch {
          // ignore
        }
      })();
    }
  }, [paramStudentId, fetchStudentInvoices]);

  const handleSelectStudent = (st: StudentOption) => {
    setSelectedStudent(st);
    setStudentResults([]);
    setStudentSearch("");
    void fetchStudentInvoices(st.id);
  };

  const handleSelectInvoice = (inv: InvoiceItem) => {
    setSelectedInvoiceId(inv.id);
    setAmount(Number(inv.due_amount).toFixed(2));
  };

  const handleSubmitPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudent) return;
    if (Number(amount) <= 0) {
      setErrorMessage(t("fees.invalidAmount", "Please enter a valid payment amount greater than zero."));
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    try {
      const paymentRes = await feesApi.recordCounterPayment({
        student_id: selectedStudent.id,
        invoice_id: selectedInvoiceId || undefined,
        amount: Number(amount),
        payment_method: paymentMethod,
        bank_name: bankName || undefined,
        cheque_no: chequeNo || undefined,
        pos_approval_code: transactionId || undefined,
        notes: notes || undefined,
      });

      const payment = paymentRes as PaymentItem;

      // Prepare receipt data
      const selectedInv = studentInvoices.find((i) => i.id === selectedInvoiceId);
      const items = selectedInv?.lines?.map((l) => ({
        head_name: l.fee_head_name,
        amount: l.payable_amount,
      })) || [
        {
          head_name: selectedInv?.title || t("fees.tuitionFee", "Fee Payment"),
          amount: amount,
        },
      ];

      setGeneratedReceipt({
        receipt_number: payment.receipt_number || `REC-${Date.now().toString().slice(-6)}`,
        payment_date: new Date().toISOString().slice(0, 10),
        payment_method: paymentMethod.toUpperCase(),
        transaction_id: transactionId || payment.transaction_id,
        student_name: selectedStudent.name_en,
        student_code: selectedStudent.student_id,
        class_name: selectedStudent.class_name,
        section_name: selectedStudent.section_name,
        roll_no: selectedStudent.roll_no,
        items,
        subtotal: amount,
        total_paid: amount,
      });

      // Refresh invoices
      void fetchStudentInvoices(selectedStudent.id);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : t("fees.paymentFailed", "Payment recording failed.");
      setErrorMessage(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const totalDuesAll = studentInvoices.reduce((acc, cur) => acc + Number(cur.due_amount || 0), 0);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <CreditCard className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t("fees.counterCollection", "Counter Collection (POS)")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("fees.posSubtitle", "Fast point-of-sale fee intake, instant money receipt generation, and MFS verification.")}
          </p>
        </div>
      </div>

      {/* Student Lookup Searchbox */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm relative">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
          {t("fees.findStudent", "Search Student (by Name, ID, or Roll Number)")}
        </label>
        <div className="relative">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("fees.searchStudentPrompt", "Type student name or ID (e.g. STU-2026-001)...")}
            value={studentSearch}
            onChange={(e) => {
              setStudentSearch(e.target.value);
              void handleSearchStudents(e.target.value);
            }}
            className="pl-10 h-11 text-base bg-slate-50 dark:bg-slate-800/40"
          />
        </div>

        {/* Search Results Dropdown */}
        {studentResults.length > 0 && (
          <div className="absolute left-5 right-5 top-20 z-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl overflow-hidden max-h-60 overflow-y-auto">
            {studentResults.map((st) => (
              <button
                key={st.id}
                type="button"
                onClick={() => handleSelectStudent(st)}
                className="w-full text-left px-4 py-3 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 border-b last:border-0 border-slate-100 dark:border-slate-800 flex items-center justify-between transition-colors"
              >
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block text-sm">{st.name_en}</span>
                  <span className="text-xs text-slate-500 font-mono">
                    ID: {st.student_id} {st.roll_no ? `| Roll: ${st.roll_no}` : ""}
                  </span>
                </div>
                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                  {st.class_name || "Class"} {st.section_name ? `(${st.section_name})` : ""}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Selected Student Profile Banner */}
        {selectedStudent && (
          <div className="mt-4 p-4 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/50 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                <User className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 dark:text-slate-100 text-base">{selectedStudent.name_en}</h3>
                <span className="text-xs text-slate-500 font-mono">
                  ID: {selectedStudent.student_id} {selectedStudent.roll_no ? `• Roll: ${selectedStudent.roll_no}` : ""}
                </span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs text-slate-500 block">{t("fees.totalDues", "Total Unpaid Dues")}</span>
              <span className="text-lg font-bold font-mono text-rose-600 dark:text-rose-400">
                ৳{totalDuesAll.toFixed(2)}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Main Payment Workspace */}
      {selectedStudent && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Column 1: Unpaid Invoices */}
          <div className="lg:col-span-2 space-y-4">
            <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 p-5 shadow-sm">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm mb-3 flex items-center justify-between">
                <span>{t("fees.pendingInvoices", "Outstanding Invoices")} ({studentInvoices.length})</span>
                <span className="text-xs font-normal text-slate-400">{t("fees.selectInvoicePrompt", "Click an invoice to collect")}</span>
              </h3>

              {loadingInvoices ? (
                <div className="p-8 text-center text-slate-400 text-sm">{t("common.loading", "Loading invoices...")}</div>
              ) : studentInvoices.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 dark:bg-slate-800/30 rounded-lg">
                  <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{t("fees.noDues", "No outstanding dues!")}</p>
                  <p className="text-xs text-slate-400 mt-1">{t("fees.studentPaidUp", "This student has no pending fee invoices.")}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {studentInvoices.map((inv) => {
                    const isSelected = selectedInvoiceId === inv.id;
                    return (
                      <div
                        key={inv.id}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") handleSelectInvoice(inv);
                        }}
                        onClick={() => handleSelectInvoice(inv)}
                        className={`p-3.5 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                          isSelected
                            ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-sm"
                            : "border-slate-200 dark:border-slate-800 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <input
                            type="radio"
                            name="invoice_selection"
                            checked={isSelected}
                            onChange={() => handleSelectInvoice(inv)}
                            className="h-4 w-4 text-emerald-600 focus:ring-emerald-500"
                          />
                          <div>
                            <span className="font-mono font-medium text-slate-900 dark:text-slate-100 block text-xs">
                              {inv.invoice_number}
                            </span>
                            <span className="text-xs text-slate-500">
                              {inv.title || inv.invoice_type} • Due: {inv.due_date || "—"}
                            </span>
                          </div>
                        </div>

                        <div className="text-right">
                          <span className="font-mono font-bold text-rose-600 dark:text-rose-400 text-sm block">
                            ৳{Number(inv.due_amount).toFixed(2)}
                          </span>
                          <span className="text-[11px] text-slate-400">Total: ৳{Number(inv.total_payable).toFixed(2)}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Column 2: Payment Intake Form */}
          <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm pb-2 border-b border-slate-100 dark:border-slate-800">
              {t("fees.intakeDetails", "Collection Details")}
            </h3>

            {errorMessage && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 rounded-lg text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={(e) => { void handleSubmitPayment(e); }} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
                  {t("fees.paymentAmount", "Amount to Collect (৳)")}
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-400 font-bold">৳</span>
                  <Input
                    type="number"
                    step="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="pl-8 text-lg font-bold font-mono h-11 text-emerald-700 dark:text-emerald-400"
                  />
                </div>
              </div>

              {/* Payment Method Selector */}
              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
                  {t("fees.paymentChannel", "Payment Method")}
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(["cash", "bkash", "nagad", "rocket", "bank", "card"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setPaymentMethod(m)}
                      className={`h-9 px-2 rounded-lg border text-xs font-semibold uppercase transition-all flex items-center justify-center gap-1 ${
                        paymentMethod === m
                          ? "border-emerald-600 bg-emerald-600 text-white shadow-sm"
                          : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
                      }`}
                    >
                      {m === "cash" && <DollarSign className="h-3.5 w-3.5" />}
                      {m === "bkash" && <Smartphone className="h-3.5 w-3.5" />}
                      {m === "nagad" && <Smartphone className="h-3.5 w-3.5" />}
                      {m === "bank" && <Building className="h-3.5 w-3.5" />}
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              {/* MFS or Bank Slip Reference */}
              {paymentMethod !== "cash" && (
                <div className="space-y-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div>
                    <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">
                      {paymentMethod === "bank" ? t("fees.bankName", "Bank & Branch Name") : t("fees.mfsTrxId", "MFS Transaction ID (TrxID)")}
                    </label>
                    <Input
                      placeholder={paymentMethod === "bank" ? "e.g. Sonali Bank, Principal Branch" : "e.g. BKS9931818"}
                      value={paymentMethod === "bank" ? bankName : transactionId}
                      onChange={(e) => {
                        if (paymentMethod === "bank") setBankName(e.target.value);
                        else setTransactionId(e.target.value);
                      }}
                      className="text-xs h-9"
                    />
                  </div>

                  {paymentMethod === "bank" && (
                    <div>
                      <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">
                        {t("fees.chequeOrSlipNo", "Deposit Slip / Cheque No.")}
                      </label>
                      <Input
                        placeholder="e.g. SLIP-129482"
                        value={chequeNo}
                        onChange={(e) => setChequeNo(e.target.value)}
                        className="text-xs h-9"
                      />
                    </div>
                  )}
                </div>
              )}

              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
                  {t("common.notes", "Notes / Remarks")}
                </label>
                <Input
                  placeholder={t("fees.notesPrompt", "Optional remarks...")}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="text-xs h-9"
                />
              </div>

              <Button
                type="submit"
                disabled={submitting || Number(amount) <= 0}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold h-11 gap-2 shadow-sm"
              >
                <Receipt className="h-4 w-4" />
                {submitting ? t("fees.processing", "Processing...") : t("fees.recordAndPrint", "Record & Print Receipt")}
              </Button>
            </form>
          </div>
        </div>
      )}

      {/* Printable Receipt Preview Modal */}
      {generatedReceipt && (
        <MoneyReceiptPreview receipt={generatedReceipt} onClose={() => setGeneratedReceipt(null)} />
      )}
    </div>
  );
}
