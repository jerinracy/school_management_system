import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FileText,
  Search,
  Filter,
  CheckCircle,
  AlertCircle,
  Clock,
  Ban,
  Layers,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormLabel, FormMessage } from "@/components/ui/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { feesApi, type InvoiceItem } from "@/features/fees/api/feesApi";
import {
  bulkInvoiceGenerateSchema,
  type BulkInvoiceGenerateFormData,
} from "@/features/fees/schemas/feeSchemas";
import { apiClient } from "@/lib/api-client";

export default function InvoicesListPage() {
  const { t } = useTranslation();

  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [sessions, setSessions] = useState<Array<{ id: string; name: string }>>([]);

  // Modals
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
  const [bulkPreviewData, setBulkPreviewData] = useState<{
    total_active_students?: number;
    new_invoices_to_create?: number;
    estimated_total_bdt?: string | number;
  } | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const bulkForm = useForm<BulkInvoiceGenerateFormData>({
    resolver: zodResolver(bulkInvoiceGenerateSchema),
    defaultValues: {
      session_id: "",
      class_level_id: "",
      billing_month: new Date().getMonth() + 1,
      billing_year: new Date().getFullYear(),
      invoice_type: "monthly",
      as_issued: true,
    },
  });

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    try {
      const res = await feesApi.getInvoices({
        search: search || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
      });
      setInvoices(((res as { results?: InvoiceItem[] }).results ?? []));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  const fetchOptions = useCallback(async () => {
    try {
      const [classRes, sessRes] = await Promise.all([
        apiClient.GET("/api/v1/academics/classes/"),
        apiClient.GET("/api/v1/institutions/sessions/"),
      ]);
      if (classRes.data && "results" in classRes.data) {
        setClasses(classRes.data.results);
      }
      if (sessRes.data && "results" in sessRes.data) {
        setSessions(sessRes.data.results);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    void fetchInvoices();
  }, [fetchInvoices]);

  useEffect(() => {
    void fetchOptions();
  }, [fetchOptions]);

  const handlePreviewBulk = async () => {
    const vals = bulkForm.getValues();
    if (!vals.session_id || !vals.class_level_id) return;
    try {
      const res = await feesApi.bulkPreviewInvoices({
        session_id: vals.session_id,
        class_level_id: vals.class_level_id,
        billing_month: vals.billing_month,
        billing_year: vals.billing_year,
        invoice_type: vals.invoice_type,
      });
      setBulkPreviewData(res);
    } catch {
      // error handled
    }
  };

  const handleBulkGenerate = async (data: BulkInvoiceGenerateFormData) => {
    setIsGenerating(true);
    try {
      await feesApi.bulkGenerateInvoices(data);
      setIsBulkModalOpen(false);
      bulkForm.reset();
      setBulkPreviewData(null);
      void fetchInvoices();
    } catch {
      // error handled
    } finally {
      setIsGenerating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "paid":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400">
            <CheckCircle className="h-3 w-3" />
            {t("fees.statusPaid", "Paid")}
          </span>
        );
      case "partially_paid":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-400">
            <Clock className="h-3 w-3" />
            {t("fees.statusPartial", "Partial")}
          </span>
        );
      case "overdue":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400">
            <AlertCircle className="h-3 w-3" />
            {t("fees.statusOverdue", "Overdue")}
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            <Ban className="h-3 w-3" />
            {t("fees.statusCancelled", "Cancelled")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400">
            <Clock className="h-3 w-3" />
            {t("fees.statusUnpaid", "Unpaid")}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <FileText className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t("fees.studentInvoices", "Student Invoices & Billing")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("fees.invoicesSubtitle", "Manage monthly tuition billing, exam vouchers, waivers, and collection status.")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={() => setIsBulkModalOpen(true)} className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white">
            <Layers className="h-4 w-4" />
            {t("fees.bulkGenerate", "Bulk Generate Invoices")}
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs text-slate-500 block">{t("fees.totalInvoices", "Total Invoices")}</span>
          <span className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">{invoices.length}</span>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs text-slate-500 block">{t("fees.paidInvoices", "Paid Count")}</span>
          <span className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
            {invoices.filter((i) => i.status === "paid").length}
          </span>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs text-slate-500 block">{t("fees.unpaidCount", "Unpaid / Pending")}</span>
          <span className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400">
            {invoices.filter((i) => i.status === "issued" || i.status === "partially_paid").length}
          </span>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <span className="text-xs text-slate-500 block">{t("fees.overdueCount", "Overdue Invoices")}</span>
          <span className="text-xl font-bold font-mono text-rose-600 dark:text-rose-400">
            {invoices.filter((i) => i.status === "overdue").length}
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder={t("fees.searchInvoicePrompt", "Search invoice # or student...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-white dark:bg-slate-900"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="h-4 w-4 text-slate-400 hidden sm:block" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm w-full sm:w-44"
          >
            <option value="all">{t("common.allStatus", "All Statuses")}</option>
            <option value="issued">{t("fees.statusUnpaid", "Unpaid / Issued")}</option>
            <option value="partially_paid">{t("fees.statusPartial", "Partially Paid")}</option>
            <option value="paid">{t("fees.statusPaid", "Paid")}</option>
            <option value="overdue">{t("fees.statusOverdue", "Overdue")}</option>
            <option value="cancelled">{t("fees.statusCancelled", "Cancelled")}</option>
          </select>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
              <tr>
                <th className="py-3 px-4">{t("fees.invoiceNo", "Invoice #")}</th>
                <th className="py-3 px-4">{t("students.student", "Student")}</th>
                <th className="py-3 px-4">{t("fees.billingPeriod", "Billing Period")}</th>
                <th className="py-3 px-4 text-right">{t("fees.totalPayable", "Total Payable")}</th>
                <th className="py-3 px-4 text-right">{t("fees.paidAmount", "Paid")}</th>
                <th className="py-3 px-4 text-right">{t("fees.dueAmount", "Due")}</th>
                <th className="py-3 px-4 text-center">{t("common.status", "Status")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading invoices...")}
                  </td>
                </tr>
              ) : invoices.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <FileText className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    {t("fees.noInvoicesFound", "No invoices match the filter criteria.")}
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-900 dark:text-slate-100">
                      {inv.invoice_number}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-800 dark:text-slate-200 block">{inv.student_name}</span>
                      <span className="font-mono text-xs text-slate-400">{inv.student_code}</span>
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600 dark:text-slate-400">
                      {inv.title || (inv.billing_month ? `Month ${inv.billing_month}/${inv.billing_year}` : inv.invoice_type)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-slate-900 dark:text-slate-100">
                      ৳{Number(inv.total_payable).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                      ৳{Number(inv.paid_amount).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-rose-600 dark:text-rose-400 font-semibold">
                      ৳{Number(inv.due_amount).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-center">{getStatusBadge(inv.status)}</td>
                    <td className="py-3 px-4 text-right">
                      <Link to={`/fees/invoices/${inv.id}`}>
                        <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs">
                          {t("common.view", "View")}
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bulk Generate Modal */}
      <Dialog open={isBulkModalOpen} onOpenChange={setIsBulkModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              {t("fees.bulkGenerateInvoices", "Bulk Generate Invoices")}
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={(e) => { void bulkForm.handleSubmit(handleBulkGenerate)(e); }} className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <FormField>
                <FormLabel>{t("academics.academicSession", "Session")}</FormLabel>
                <select
                  {...bulkForm.register("session_id")}
                  onChange={(e) => {
                    bulkForm.setValue("session_id", e.target.value);
                    void handlePreviewBulk();
                  }}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="">{t("common.select", "Select Session...")}</option>
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                <FormMessage>{bulkForm.formState.errors.session_id?.message}</FormMessage>
              </FormField>

              <FormField>
                <FormLabel>{t("academics.class", "Class")}</FormLabel>
                <select
                  {...bulkForm.register("class_level_id")}
                  onChange={(e) => {
                    bulkForm.setValue("class_level_id", e.target.value);
                    void handlePreviewBulk();
                  }}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="">{t("common.select", "Select Class...")}</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <FormMessage>{bulkForm.formState.errors.class_level_id?.message}</FormMessage>
              </FormField>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <FormField>
                <FormLabel>{t("fees.invoiceType", "Billing Type")}</FormLabel>
                <select
                  {...bulkForm.register("invoice_type")}
                  className="w-full h-10 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
                >
                  <option value="monthly">Monthly</option>
                  <option value="term">Term / Semester</option>
                  <option value="annual">Annual</option>
                  <option value="admission">Admission</option>
                </select>
              </FormField>

              <FormField>
                <FormLabel>{t("fees.billingMonth", "Month (1-12)")}</FormLabel>
                <Input {...bulkForm.register("billing_month", { valueAsNumber: true })} type="number" min={1} max={12} />
              </FormField>

              <FormField>
                <FormLabel>{t("fees.billingYear", "Year")}</FormLabel>
                <Input {...bulkForm.register("billing_year", { valueAsNumber: true })} type="number" />
              </FormField>
            </div>

            <FormField>
              <FormLabel>{t("fees.dueDate", "Due Date")}</FormLabel>
              <Input {...bulkForm.register("due_date")} type="date" />
            </FormField>

            {/* Live Preview Count Box */}
            {bulkPreviewData && (
              <div className="p-3.5 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs space-y-1">
                <div className="flex justify-between font-medium">
                  <span className="text-slate-600 dark:text-slate-300">{t("fees.activeStudents", "Active Students in Class")}:</span>
                  <span className="font-bold">{bulkPreviewData.total_active_students || 0}</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span className="text-slate-600 dark:text-slate-300">{t("fees.invoicesToCreate", "New Invoices to Generate")}:</span>
                  <span className="font-bold text-emerald-700 dark:text-emerald-400">
                    {bulkPreviewData.new_invoices_to_create || 0}
                  </span>
                </div>
                {bulkPreviewData.estimated_total_bdt ? (
                  <div className="flex justify-between font-medium pt-1 border-t border-emerald-200 dark:border-emerald-800">
                    <span className="text-slate-600 dark:text-slate-300">{t("fees.estimatedBilling", "Estimated Total Amount")}:</span>
                    <span className="font-bold font-mono text-emerald-700 dark:text-emerald-400">
                      ৳{Number(bulkPreviewData.estimated_total_bdt).toFixed(2)}
                    </span>
                  </div>
                ) : null}
              </div>
            )}

            <DialogFooter className="mt-4">
              <Button type="button" variant="outline" onClick={() => setIsBulkModalOpen(false)}>
                {t("common.cancel", "Cancel")}
              </Button>
              <Button type="submit" disabled={isGenerating} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {isGenerating ? t("common.generating", "Generating...") : t("fees.generateNow", "Generate Invoices")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
