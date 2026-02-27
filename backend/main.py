#!/usr/bin/env python3
"""
IBKR WHT FastAPI Backend - Fixed Ragged CSV Parsing & Refund Logic
"""

import io
import os
import logging
import csv
from contextlib import contextmanager
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text, Column, String, Date, Float, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# ---------------------------------------------------------------------------
# Setup Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ibkr-api")

# ---------------------------------------------------------------------------
# App & DB Setup
# ---------------------------------------------------------------------------
app = FastAPI(title="IBKR WHT API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.getenv("DB_HOST", "192.168.0.129")
DB_USER = os.getenv("DB_USER", "ibkr_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "230479")
DB_NAME = os.getenv("DB_NAME", "ibkr_wht")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_type = Column(String(255))
    currency = Column(String(10))
    date = Column(Date)
    ticker = Column(String(50))
    # Note: detail is unique. If IBKR provides identical descriptions for 
    # tax and refund, we must make them unique during import.
    detail = Column(String(255), unique=True)
    amount = Column(Float)

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"DB Error: {e}")
        db.rollback()
        raise HTTPException(status_code=503, detail="Database error")
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------

def extract_ticker(desc: str) -> str:
    if not desc: return "UNKNOWN"
    # Handles "SGOV(US46436E7186)..." or "939 (CNE...)"
    first_part = desc.split('(')[0].strip()
    return first_part.split(' ')[0].upper()

def parse_ibkr_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    Robustly parses IBKR CSV by reading line-by-line to handle varying column counts.
    """
    decoded_file = file_bytes.decode('utf-8').splitlines()
    reader = csv.reader(decoded_file)
    
    extracted_rows = []
    
    # Target sections
    targets = {"Dividends", "Withholding Tax", "Payment In Lieu of Dividends"}

    for row in reader:
        if not row or len(row) < 6:
            continue
        
        section = row[0]
        label = row[1] # 'Data' or 'Header'
        
        if section in targets and label == "Data":
            # Skip 'Total' rows within sections
            if "Total" in row[2] or "Total" in row[3]:
                continue
                
            currency = row[2]
            date_str = row[3]
            description = row[4]
            amount_str = row[5]
            
            # We only care about USD for this specific WHT report
            if currency != "USD":
                continue

            try:
                extracted_rows.append({
                    "item_type": "Dividends" if section != "Withholding Tax" else "Withholding Tax",
                    "currency": currency,
                    "date": date_str,
                    "detail": description,
                    "amount": float(amount_str)
                })
            except ValueError:
                continue

    df = pd.DataFrame(extracted_rows)
    if df.empty:
        return df

    df["ticker"] = df["detail"].apply(extract_ticker)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

def generate_report_data(df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
    """
    Aggregates data into the final WHT Refund report.
    """
    if df.empty:
        return [], []

    # Group by ticker and item_type
    grouped = df.groupby(["ticker", "item_type"])["amount"].sum().unstack(fill_value=0)
    
    # Ensure columns exist even if no data for one type
    for col in ["Dividends", "Withholding Tax"]:
        if col not in grouped.columns:
            grouped[col] = 0.0

    # In IBKR: 
    # - Dividends are usually positive.
    # - WHT Paid is negative.
    # - WHT Refund is positive.
    # We need to separate Paid and Refunded from the 'Withholding Tax' item_type.
    # Since we only have the sum per ticker above, let's refine the grouping:
    
    report_list = []
    tickers = df["ticker"].unique()
    
    for ticker in tickers:
        t_data = df[df["ticker"] == ticker]
        
        div_sum = t_data[t_data["item_type"] == "Dividends"]["amount"].sum()
        tax_rows = t_data[t_data["item_type"] == "Withholding Tax"]
        
        paid = tax_rows[tax_rows["amount"] < 0]["amount"].sum() * -1
        refunded = tax_rows[tax_rows["amount"] > 0]["amount"].sum()
        
        net_wht = paid - refunded
        final_amt = div_sum - net_wht
        
        report_list.append({
            "SYMBOL": ticker,
            "Total Dividends": div_sum,
            "Total WHT Paid": paid,
            "Total WHT Refunded": refunded,
            "Net WHT": net_wht,
            "Final Amount": final_amt,
            "WHT Refund %": (refunded / paid * 100) if paid > 0 else 0,
            "Final Amount %": (final_amt / div_sum * 100) if div_sum > 0 else 0
        })

    report_df = pd.DataFrame(report_list).sort_values("SYMBOL")
    
    # Grand Total
    totals = {
        "SYMBOL": "GRAND TOTAL",
        "Total Dividends": report_df["Total Dividends"].sum(),
        "Total WHT Paid": report_df["Total WHT Paid"].sum(),
        "Total WHT Refunded": report_df["Total WHT Refunded"].sum(),
        "Net WHT": report_df["Net WHT"].sum(),
        "Final Amount": report_df["Final Amount"].sum()
    }
    totals["WHT Refund %"] = (totals["Total WHT Refunded"] / totals["Total WHT Paid"] * 100) if totals["Total WHT Paid"] > 0 else 0
    totals["Final Amount %"] = (totals["Final Amount"] / totals["Total Dividends"] * 100) if totals["Total Dividends"] > 0 else 0
    
    raw_data = report_df.to_dict(orient="records")
    raw_data.append(totals)

    # Formatting
    fmt_data = []
    for row in raw_data:
        f_row = row.copy()
        for k, v in f_row.items():
            if isinstance(v, float):
                if "%" in k: f_row[k] = f"{v:.2f}%"
                else: f_row[k] = f"{v:,.2f}"
        fmt_data.append(f_row)

    return raw_data, fmt_data

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/import-csv")
async def import_csv(file: UploadFile = File(...)):
    content = await file.read()
    try:
        df = parse_ibkr_csv(content)
        if df.empty:
            return {"message": "No USD dividend/tax data found", "inserted": 0}

        inserted = 0
        skipped = 0
        with get_db_session() as db:
            # Load existing details to prevent duplicates
            existing = {res[0] for res in db.query(Transaction.detail).all()}
            
            for _, row in df.iterrows():
                # IBKR sometimes uses the exact same description for tax and refund.
                # To satisfy the DB 'unique' constraint, we append the amount if needed.
                unique_detail = row["detail"]
                if unique_detail in existing:
                    # Try making it unique by appending amount
                    unique_detail = f"{row['detail']} | {row['amount']}"
                
                if unique_detail not in existing:
                    db.add(Transaction(
                        item_type=row["item_type"],
                        currency=row["currency"],
                        date=row["date"],
                        ticker=row["ticker"],
                        detail=unique_detail,
                        amount=row["amount"]
                    ))
                    existing.add(unique_detail)
                    inserted += 1
                else:
                    skipped += 1
            db.commit()

        return {"status": "success", "inserted": inserted, "skipped": skipped}
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/getreport")
def get_report():
    with get_db_session() as db:
        df = pd.read_sql(text("SELECT * FROM transactions WHERE currency = 'USD'"), db.bind)
    
    raw, fmt = generate_report_data(df)
    return {"report": fmt, "raw": raw}

@app.get("/api/detail/{ticker}")
def get_detail(ticker: str):
    with get_db_session() as db:
        query = text("SELECT * FROM transactions WHERE ticker = :t AND currency = 'USD' ORDER BY date DESC")
        df = pd.read_sql(query, db.bind, params={"t": ticker.upper()})
    
    return {"ticker": ticker, "rows": df.to_dict(orient="records") if not df.empty else []}

@app.get("/api/health")
def health():
    return {"status": "ok"}