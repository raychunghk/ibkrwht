# IBKR Dividend & WHT Web App

Interactive web application for analysing Interactive Brokers dividend and withholding-tax (WHT) statements.

---

## Architecture

```
project/
├── backend/          # FastAPI Python backend  (port 3900)
│   ├── main.py       # API routes
│   ├── requirements.txt
│   └── start.sh
├── frontend/         # Next.js 16 frontend      (port 3100, basePath /absproxy/3100)
│   ├── app/
│   │   ├── page.tsx                  # Main report page
│   │   └── detail/[ticker]/page.tsx  # Drill-down detail page (opens in new tab)
│   ├── components/
│   │   ├── ReportTable.tsx   # TanStack Table v8 report
│   │   └── CsvImporter.tsx   # CSV upload widget
│   ├── lib/types.ts
│   └── next.config.ts        # basePath + /api/* → localhost:3900 rewrite
├── ibkrtxfcsv.py     # CLI: CSV → MariaDB (duplicate-safe)
├── ibkr_wht_combined.py  # CLI: combined import + report
├── whtreport.py      # CLI: report generator
└── schema_ddl.sql    # MariaDB schema (includes UNIQUE constraint)
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI** | Most popular modern Python API framework; async, auto-docs at `/docs`, fast |
| Frontend | **Next.js 16** | Industry standard React framework with built-in routing and API proxy |
| Table UI | **TanStack Table v8** | Gold-standard headless table for React — sorting, filtering, fully customisable |
| DB | **MariaDB** | Existing setup |

---

## 1 — Duplicate Prevention

The `transactions` table has a **`UNIQUE KEY`** on `(item_type, currency, date, ticker, amount)`.  
All inserts use **`INSERT IGNORE`**, so re-importing the same CSV is safe — existing rows are silently skipped and a count of inserted vs skipped is returned.

```sql
-- Schema change (run once if table already exists)
ALTER TABLE transactions
  ADD UNIQUE KEY uq_transaction (item_type, currency, date, ticker, amount);
```

---

## 2 — Running the Backend

```bash
cd backend
pip install -r requirements.txt
./start.sh
# → http://localhost:3900
# → Swagger UI: http://localhost:3900/docs
```

Override DB credentials via environment variables:
```bash
DB_HOST=192.168.0.129 DB_USER=root DB_PASSWORD="pwd 230479" ./start.sh
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/import-csv` | Upload IBKR CSV, returns insert/skip counts |
| GET | `/api/getreport` | Returns formatted + raw report rows |
| GET | `/api/detail/{ticker}` | Returns all raw transactions for a ticker |

---

## 3 — Running the Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3100/absproxy/3100
```

### VS Code Server access

When using VS Code Server (e.g. `code2.raygor.cc`), the URL pattern is:

```
https://code2.raygor.cc/absproxy/3100/          ← Main report page
https://code2.raygor.cc/absproxy/3100/detail/AAPL  ← Drill-down for AAPL
```

The `next.config.ts` rewrites `/api/*` → `http://localhost:3900/api/*`, so the
frontend never needs to know the backend's external URL.

---

## 4 — Table UI: TanStack Table v8

**TanStack Table** (formerly React Table) is the recommended choice because:
- **Headless** — zero opinionated styles, you own the markup
- **Sortable columns** — click any header to sort
- **TypeScript-first** — full generic type inference on row data
- **Tiny** — ~14 kB gzipped
- **Best ecosystem** — pairs with shadcn/ui, Tailwind, or any styling approach

---

## 5 — Drill-down Detail Rows

Click any value in the **"Final Amount % 🔍"** column (last column) on any non-Grand-Total row.  
A **new browser tab** opens at `/detail/<TICKER>` showing:
- Summary cards (Total Dividends, WHT Paid, WHT Refunded)
- Sortable table of every raw transaction row for that ticker (date, type, description, amount)
