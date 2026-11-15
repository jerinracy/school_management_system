import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { AlertCircle, CreditCard, Users, Filter, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { feesApi, type DueListItem } from "@/features/fees/api/feesApi";
import { apiClient } from "@/lib/api-client";

export default function DueListPage() {
  const { t } = useTranslation();

  const [dueList, setDueList] = useState<DueListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [minDaysOverdue, setMinDaysOverdue] = useState<number>(0);

  const fetchDueList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await feesApi.getDueList({
        class_level: selectedClass || undefined,
        min_days_overdue: minDaysOverdue > 0 ? minDaysOverdue : undefined,
      });
      setDueList(((res as { results?: DueListItem[] }).results ?? []));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [selectedClass, minDaysOverdue]);

  const fetchClasses = useCallback(async () => {
    try {
      const res = await apiClient.GET("/api/v1/academics/classes/");
      if (res.data && "results" in res.data) {
        setClasses(res.data.results);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    void fetchDueList();
  }, [fetchDueList]);

  useEffect(() => {
    void fetchClasses();
  }, [fetchClasses]);

  const totalOutstanding = dueList.reduce((acc, cur) => acc + Number(cur.total_due_amount || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <AlertCircle className="h-6 w-6 text-rose-600 dark:text-rose-400" />
            {t("fees.dueListDefaulters", "Fee Due List & Defaulters")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("fees.dueListSubtitle", "Track overdue student tuition balances, invoice counts, and collection follow-up.")}
          </p>
        </div>

        <Button variant="outline" onClick={() => window.print()} className="gap-2">
          <Printer className="h-4 w-4" />
          {t("common.print", "Print Report")}
        </Button>
      </div>

      {/* KPI Banners */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 block">{t("fees.totalDefaulters", "Total Defaulters")}</span>
            <span className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">{dueList.length}</span>
          </div>
          <div className="p-3 bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 rounded-xl">
            <Users className="h-6 w-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 block">{t("fees.totalOutstandingDues", "Total Outstanding Receivables")}</span>
            <span className="text-2xl font-bold font-mono text-rose-600 dark:text-rose-400">
              ৳{totalOutstanding.toFixed(2)}
            </span>
          </div>
          <div className="p-3 bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 rounded-xl">
            <CreditCard className="h-6 w-6" />
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-slate-50 dark:bg-slate-800/40 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold uppercase text-slate-500">{t("common.filterBy", "Filter")}:</span>
        </div>

        <select
          value={selectedClass}
          onChange={(e) => setSelectedClass(e.target.value)}
          className="h-9 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs"
        >
          <option value="">{t("academics.allClasses", "All Classes")}</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <select
          value={minDaysOverdue}
          onChange={(e) => setMinDaysOverdue(Number(e.target.value))}
          className="h-9 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs"
        >
          <option value={0}>{t("fees.anyOverdue", "Any Overdue Time")}</option>
          <option value={15}>{t("fees.overdue15Days", "15+ Days Overdue")}</option>
          <option value={30}>{t("fees.overdue30Days", "30+ Days Overdue")}</option>
          <option value={60}>{t("fees.overdue60Days", "60+ Days Overdue")}</option>
          <option value={90}>{t("fees.overdue90Days", "90+ Days Overdue")}</option>
        </select>
      </div>

      {/* Table */}
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
              <tr>
                <th className="py-3 px-4">{t("students.roll", "Roll")}</th>
                <th className="py-3 px-4">{t("students.student", "Student Name")}</th>
                <th className="py-3 px-4">{t("academics.class", "Class")} / {t("academics.section", "Sec")}</th>
                <th className="py-3 px-4 text-center">{t("fees.unpaidInvoices", "Unpaid Invoices")}</th>
                <th className="py-3 px-4">{t("fees.oldestOverdue", "Oldest Due Date")}</th>
                <th className="py-3 px-4 text-right">{t("fees.totalDue", "Total Due (৳)")}</th>
                <th className="py-3 px-4 text-right">{t("common.actions", "Actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading due list...")}
                  </td>
                </tr>
              ) : dueList.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <AlertCircle className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                    {t("fees.noDefaulters", "Congratulations! No students match the overdue criteria.")}
                  </td>
                </tr>
              ) : (
                dueList.map((st) => (
                  <tr key={st.student_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-700 dark:text-slate-300">
                      {st.roll_no ? `#${st.roll_no}` : "—"}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-900 dark:text-slate-100 block">{st.student_name_en}</span>
                      <span className="font-bengali text-xs text-slate-400">{st.student_name_bn}</span>
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {st.class_name} {st.section_name ? `(${st.section_name})` : ""}
                    </td>
                    <td className="py-3 px-4 text-center font-mono font-semibold text-rose-600 dark:text-rose-400">
                      {st.unpaid_invoice_count}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-slate-500">
                      {st.oldest_overdue_date || "—"}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-rose-600 dark:text-rose-400 text-base">
                      ৳{Number(st.total_due_amount).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link to={`/fees/collect?student_id=${st.student_id}`}>
                        <Button size="sm" className="h-8 gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs">
                          <CreditCard className="h-3.5 w-3.5" />
                          {t("fees.collect", "Collect")}
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
    </div>
  );
}
