"use client";

import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ReportRow } from "@/lib/types";
import { apiUrl } from "@/lib/api";

const columnHelper = createColumnHelper<ReportRow>();

const NUMERIC_COLS: (keyof ReportRow)[] = [
  "Total Dividends",
  "Total WHT Paid",
  "Total WHT Refunded",
  "Net WHT",
  "Final Amount",
  "WHT Refund %",
  "Final Amount %",
];

function openDetailTab(ticker: string) {
  const url = apiUrl(`/detail/${encodeURIComponent(ticker)}`);
  window.open(url, "_blank");
}

const columns = [
  columnHelper.accessor("SYMBOL", {
    header: "Symbol",
    cell: (info) => (
      <span className="font-semibold text-blue-700">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor("Total Dividends", {
    header: "Total Dividends",
    cell: (info) => (
      <span className="tabular-nums text-right block">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor("Total WHT Paid", {
    header: "WHT Paid",
    cell: (info) => (
      <span className="tabular-nums text-right block text-red-600">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("Total WHT Refunded", {
    header: "WHT Refunded",
    cell: (info) => (
      <span className="tabular-nums text-right block text-green-600">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("Net WHT", {
    header: "Net WHT",
    cell: (info) => (
      <span className="tabular-nums text-right block">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor("WHT Refund %", {
    header: "WHT Refund %",
    cell: (info) => (
      <span className="tabular-nums text-right block">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor("Final Amount", {
    header: "Final Amount",
    cell: (info) => (
      <span className="tabular-nums text-right block font-medium">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("Final Amount %", {
    id: "final_pct",
    header: () => (
      <span title="Click any cell in this column to view transaction details">
        Final Amount % 🔍
      </span>
    ),
    cell: (info) => {
      const symbol = info.row.original.SYMBOL;
      const isGrandTotal = symbol === "Grand Total";
      return (
        <button
          onClick={() => !isGrandTotal && openDetailTab(symbol)}
          disabled={isGrandTotal}
          className={[
            "tabular-nums text-right block w-full px-1 rounded transition-colors",
            isGrandTotal
              ? "cursor-default"
              : "cursor-pointer text-blue-600 underline decoration-dotted hover:bg-blue-50 hover:text-blue-800",
          ].join(" ")}
          title={isGrandTotal ? undefined : `View detail rows for ${symbol}`}
        >
          {info.getValue()}
        </button>
      );
    },
  }),
];

interface Props {
  data: ReportRow[];
}

export default function ReportTable({ data }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const nonTotal = data.filter((r) => r.SYMBOL !== "Grand Total");
  const grandTotal = data.find((r) => r.SYMBOL === "Grand Total");
  const sorted = [...nonTotal];
  const tableData = grandTotal ? [...sorted, grandTotal] : sorted;

  const table = useReactTable({
    data: tableData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-100">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => {
                const canSort = header.column.getCanSort();
                return (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className={[
                      "px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap",
                      canSort ? "cursor-pointer select-none hover:bg-gray-200" : "",
                    ].join(" ")}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === "asc"
                      ? " ▲"
                      : header.column.getIsSorted() === "desc"
                      ? " ▼"
                      : ""}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {table.getRowModel().rows.map((row) => {
            const isGrandTotal = row.original.SYMBOL === "Grand Total";
            return (
              <tr
                key={row.id}
                className={[
                  isGrandTotal
                    ? "bg-blue-50 font-bold border-t-2 border-blue-300"
                    : "hover:bg-gray-50",
                ].join(" ")}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-2.5 whitespace-nowrap">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
