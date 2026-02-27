export interface ReportRow {
  SYMBOL: string;
  "Total Dividends": string;
  "Total WHT Paid": string;
  "Total WHT Refunded": string;
  "Net WHT": string;
  "Final Amount": string;
  "WHT Refund %": string;
  "Final Amount %": string;
}

export interface RawReportRow {
  SYMBOL: string;
  "Total Dividends": number;
  "Total WHT Paid": number;
  "Total WHT Refunded": number;
  "Net WHT": number;
  "Final Amount": number;
  "WHT Refund %": number;
  "Final Amount %": number;
}

export interface TransactionRow {
  id?: number;
  item_type: string;
  currency: string;
  date: string;
  ticker: string;
  detail: string;
  amount: number;
  wht_type?: string | null;
  included_in_report?: boolean;
}

export interface ImportResult {
  message: string;
  dividends_found: number;
  wht_found: number;
  total: number;
  inserted: number;
  skipped: number;
}
