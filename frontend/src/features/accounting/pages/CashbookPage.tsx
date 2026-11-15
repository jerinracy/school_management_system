import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen, Calendar, Printer, ArrowDownLeft, ArrowUpRight, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { accountingApi, type CashbookStatement, type AccountItem } from "@/features/accounting/api/accountingApi";

export default function CashbookPage() {
  const { t } = useTranslation();

  const [date, setDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [statement, setStatement] = useState<CashbookStatement | null>(null);
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const fetchCashbook = useCallback(async () => {
    setLoading(true);
    try {
      const data = await accountingApi.getCashbook(date, selectedAccountId || undefined);
      setStatement(data);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  }, [date, selectedAccountId]);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await accountingApi.getAccounts({ account_type: "asset" });
      if (res && "results" in res) {
        setAccounts((res as { results: AccountItem[] }).results);
      }
    } catch {
      // handled
    }
  }, []);

  useEffect(() => {
    void fetchCashbook();
  }, [fetchCashbook]);

  useEffect(() => {
    void fetchAccounts();
  }, [fetchAccounts]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            {t("accounting.dailyCashbook", "Daily Cashbook / Day Book")}
          </h1>
          <p className="text-sm text-slate-500">
            {t("accounting.cashbookSubtitle", "Daily cash and bank inflows, disbursements, and cash drawer reconciliation.")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => window.print()} className="gap-2">
            <Printer className="h-4 w-4" />
            {t("common.print", "Print Statement")}
          </Button>
        </div>
      </div>

      {/* Date & Account Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-slate-400" />
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              {t("accounting.statementDate", "Date")}:
            </span>
          </div>
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-40 h-9 text-xs bg-slate-50 dark:bg-slate-800/40"
          />

          <select
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="h-9 px-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs w-52"
          >
            <option value="">{t("accounting.defaultCashAccount", "Cash in Hand (Default)")}</option>
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.name_en} ({acc.account_code})
              </option>
            ))}
          </select>
        </div>

        {statement && (
          <div className="text-xs text-slate-500">
            {t("accounting.account", "Account")}: <strong className="text-slate-800 dark:text-slate-200">{statement.account_name} ({statement.account_code})</strong>
          </div>
        )}
      </div>

      {/* KPI Balance Cards */}
      {statement && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <span className="text-xs text-slate-400 block">{t("accounting.openingBalance", "Opening Balance")}</span>
            <span className="text-lg font-bold font-mono text-slate-800 dark:text-slate-200">
              ৳{Number(statement.opening_balance).toFixed(2)}
            </span>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div className="flex items-center gap-1.5 text-emerald-600 text-xs font-medium">
              <ArrowDownLeft className="h-4 w-4" />
              <span>{t("accounting.totalReceipts", "Total Receipts (+)")}</span>
            </div>
            <span className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1 block">
              ৳{Number(statement.total_receipts).toFixed(2)}
            </span>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div className="flex items-center gap-1.5 text-rose-600 text-xs font-medium">
              <ArrowUpRight className="h-4 w-4" />
              <span>{t("accounting.totalPayments", "Disbursements (-)")}</span>
            </div>
            <span className="text-lg font-bold font-mono text-rose-600 dark:text-rose-400 mt-1 block">
              ৳{Number(statement.total_payments).toFixed(2)}
            </span>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <span className="text-xs text-slate-400 block">{t("accounting.closingBalance", "Closing Balance")}</span>
            <span className="text-xl font-bold font-mono text-emerald-700 dark:text-emerald-300">
              ৳{Number(statement.closing_balance).toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Transactions Register Table */}
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
            {t("accounting.dayTransactions", "Day's Journal & Cash Transactions")}
          </h3>
          <span className="text-xs text-slate-500 font-mono">
            {statement?.transactions.length || 0} {t("common.records", "records")}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-slate-50/50 dark:bg-slate-800/20 text-slate-500 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold">
              <tr>
                <th className="py-3 px-4">{t("accounting.voucherNo", "Voucher #")}</th>
                <th className="py-3 px-4">{t("accounting.voucherType", "Type")}</th>
                <th className="py-3 px-4">{t("accounting.narration", "Particulars / Narration")}</th>
                <th className="py-3 px-4">{t("accounting.party", "Payee / Payer")}</th>
                <th className="py-3 px-4 text-right text-emerald-600">{t("accounting.receiptDebit", "Receipt (Debit ৳)")}</th>
                <th className="py-3 px-4 text-right text-rose-600">{t("accounting.paymentCredit", "Payment (Credit ৳)")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    {t("common.loading", "Loading cashbook statement...")}
                  </td>
                </tr>
              ) : !statement || statement.transactions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <DollarSign className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    {t("accounting.noTransactionsToday", "No cash or bank transactions recorded on this date.")}
                  </td>
                </tr>
              ) : (
                statement.transactions.map((trx, index) => (
                  <tr key={index} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-900 dark:text-slate-100">
                      {trx.voucher_no}
                    </td>
                    <td className="py-3 px-4 uppercase text-xs font-semibold text-slate-500">
                      {trx.voucher_type}
                    </td>
                    <td className="py-3 px-4 text-slate-700 dark:text-slate-300">
                      {trx.narration}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 text-xs">
                      {trx.payee_or_payer || "—"}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      {Number(trx.receipt_amount) > 0 ? `৳${Number(trx.receipt_amount).toFixed(2)}` : "—"}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-rose-600 dark:text-rose-400">
                      {Number(trx.payment_amount) > 0 ? `৳${Number(trx.payment_amount).toFixed(2)}` : "—"}
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
