"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from "@tanstack/react-table";
import { TransactionRow } from "@/lib/types";
import { apiUrl } from "@/lib/api";

const columnHelper = createColumnHelper<TransactionRow>();

const columns = [
  columnHelper.accessor("date", {
    header: "Date",
    cell: (info) => <span className="font-mono text-sm">{info.getValue()}</span>,
  }),
  columnHelper.accessor("item_type", {
    header: "Type",
    cell: (info) => {
      const v = info.getValue();
      return (
        <span
          className={
            v === "Dividends"
              ? "text-green-700 font-medium"
              : "text-red-600 font-medium"
          }
        >
          {v}
        </span>
      );
    },
  }),
  columnHelper.accessor("currency", { header: "Currency" }),
  columnHelper.accessor("detail", {
    header: "Description",
    cell: (info) => (
      <span className="text-xs text-gray-600 max-w-xs truncate block" title={info.getValue()}>
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("amount", {
    header: "Amount",
    cell: (info) => {
      const v = info.getValue();
      return (
        <span
          className={[
            "tabular-nums text-right block font-medium",
            v < 0 ? "text-red-600" : "text-green-700",
          ].join(" ")}
        >
          {v.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}
        </span>
      );
    },
  }),
];

export default function DetailPage() {
  const params = useParams();
  const ticker = decodeURIComponent(params.ticker as string);

  const [rows, setRows] = useState<TransactionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: false }]);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(apiUrl(`/api/detail/${encodeURIComponent(ticker)}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRows(data.rows ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load detail");
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const dividends = rows
    .filter((r) => r.item_type === "Dividends")
    .reduce((s, r) => s + r.amount, 0);
  const whtPaid = rows
    .filter((r) => r.item_type === "Withholding Tax" && r.amount < 0)
    .reduce((s, r) => s + r.amount, 0);
  const whtRefunded = rows
    .filter((r) => r.item_type === "Withholding Tax" && r.amount > 0)
    .reduce((s, r) => s + r.amount, 0);

  const fmt = (n: number) =>
    n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => window.close()}
          className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded px-3 py-1"
        >
          ✕ Close
        </button>
        <h1 className="text-xl font-bold text-gray-800">
          Transaction Detail — <span className="text-blue-700">{ticker}</span>
        </h1>
      </div>

      {!loading && !error && rows.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-xs text-green-600 font-semibold uppercase mb-1">Total Dividends</div>
            <div className="text-lg font-bold text-green-800">${fmt(dividends)}</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-xs text-red-600 font-semibold uppercase mb-1">WHT Paid</div>
            <div className="text-lg font-bold text-red-800">${fmt(Math.abs(whtPaid))}</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-xs text-blue-600 font-semibold uppercase mb-1">WHT Refunded</div>
            <div className="text-lg font-bold text-blue-800">${fmt(whtRefunded)}</div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
          Loading transactions…
        </div>
      ) : rows.length === 0 ? (
        <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
          No transactions found for {ticker}.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-100">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      onClick={header.column.getToggleSortingHandler()}
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap cursor-pointer select-none hover:bg-gray-200"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() === "asc"
                        ? " ▲"
                        : header.column.getIsSorted() === "desc"
                        ? " ▼"
                        : ""}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-2.5 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-2 text-xs text-gray-400 border-t border-gray-100 bg-gray-50">
            {rows.length} transaction{rows.length !== 1 ? "s" : ""}
          </div>
        </div>
      )}
    </div>
  );
}
