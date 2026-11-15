import { apiClient } from "@/lib/api-client";
import { parseApiError } from "@/lib/errors";

export interface CashbookTransaction {
  voucher_no: string;
  voucher_type: string;
  narration: string;
  payee_or_payer?: string | null;
  cheque_no?: string | null;
  receipt_amount: string | number;
  payment_amount: string | number;
}

export interface CashbookStatement {
  account_id: string;
  account_code: string;
  account_name: string;
  date: string;
  opening_balance: string | number;
  total_receipts: string | number;
  total_payments: string | number;
  closing_balance: string | number;
  transactions: CashbookTransaction[];
}

export interface AccountItem {
  id: string;
  account_code: string;
  name_en: string;
  name_bn: string;
  account_type: "asset" | "liability" | "equity" | "revenue" | "expense";
  balance?: string | number;
  is_active: boolean;
}

function checkResponse<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (!res.response.ok) {
    throw parseApiError(res.response.status, res.error);
  }
  return res.data as T;
}

export const accountingApi = {
  async getCashbook(date?: string, accountId?: string): Promise<CashbookStatement> {
    const query: Record<string, string> = {};
    if (date) query.date = date;
    if (accountId) query.account_id = accountId;

    const res = await apiClient.GET("/api/v1/accounting/cashbook/", {
      params: Object.keys(query).length > 0 ? { query: query as never } : undefined,
    });
    return checkResponse(res) as unknown as CashbookStatement;
  },

  async getAccounts(params?: { account_type?: string; is_active?: boolean; page?: number }) {
    const res = await apiClient.GET("/api/v1/accounting/accounts/", {
      params: { query: params as never },
    });
    return checkResponse(res);
  },
};
