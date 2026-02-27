"use client";

import { useEffect, useState, useCallback } from "react";
import ReportTable from "@/components/ReportTable";
import CsvImporter from "@/components/CsvImporter";
import { ReportRow } from "@/lib/types";
import { apiUrl } from "@/lib/api";

export default function HomePage() {
  const [report, setReport] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(apiUrl("/api/getreport"));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setReport(data.report ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            IBKR Dividend &amp; WHT Report
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Withholding tax analysis — click <strong>Final Amount %</strong> on any
            row to drill into individual transactions
          </p>
        </div>
        <button
          onClick={fetchReport}
          disabled={loading}
          className="px-4 py-2 text-sm font-medium rounded border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {loading ? "Loading…" : "↺ Refresh"}
        </button>
      </div>

      <CsvImporter onImported={fetchReport} />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
          Loading report…
        </div>
      ) : report.length === 0 ? (
        <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
          No data yet — import a CSV file to get started.
        </div>
      ) : (
        <ReportTable data={report} />
      )}
    </div>
  );
}
