"use client";

import { useState, useRef } from "react";
import { ImportResult } from "@/lib/types";
import { apiUrl } from "@/lib/api";

interface Props {
  onImported: () => void;
}

export default function CsvImporter({ onImported }: Props) {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file) return;
    setStatus("loading");
    setResult(null);
    setErrorMsg("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(apiUrl("/api/import-csv"), {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Import failed");
      }
      const data: ImportResult = await res.json();
      setResult(data);
      setStatus("success");
      onImported();
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Unknown error");
      setStatus("error");
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
      <h2 className="text-base font-semibold text-gray-700 mb-3">Import IBKR CSV Statement</h2>
      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={handleChange}
          className="hidden"
          id="csv-upload"
        />
        <label
          htmlFor="csv-upload"
          className={[
            "cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded text-sm font-medium border transition-colors",
            status === "loading"
              ? "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
              : "bg-white text-blue-600 border-blue-400 hover:bg-blue-50",
          ].join(" ")}
        >
          {status === "loading" ? "Importing…" : "Choose CSV file"}
        </label>

        {status === "success" && result && (
          <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-1.5">
            ✓ {result.inserted} inserted, {result.skipped} duplicates skipped
            &nbsp;·&nbsp; {result.dividends_found} dividends, {result.wht_found} WHT rows
          </div>
        )}
        {status === "error" && (
          <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-1.5">
            ✗ {errorMsg}
          </div>
        )}
      </div>
      <p className="mt-2 text-xs text-gray-400">
        Re-importing the same file is safe — duplicate rows (same date, ticker, amount) are automatically skipped.
      </p>
    </div>
  );
}
