#!/usr/bin/env python3
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Reuse your existing DB config logic (or hardcode test values)
DB_HOST = os.getenv("DB_HOST", "192.168.0.129")
DB_USER = os.getenv("DB_USER", "ibkr_app")
DB_PASSWORD = os.getenv("DB_PASSWORD")  # set via env or hardcode temporarily for testing
DB_NAME = "ibkr_wht_test"               # ← use a separate test database!
DB_PORT = 3306

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Copy-paste your get_ticker_detail_rows function here (with fix applied)
def get_ticker_detail_rows(ticker: str, session_factory=SessionLocal) -> list[dict]:
    with session_factory() as db:
        df = pd.read_sql(
            text("""
            SELECT item_type, currency, date, ticker, detail, amount
            FROM transactions
            WHERE currency = 'USD' AND ticker = %(ticker)s
            ORDER BY date, item_type
            """),
            con=db.bind,
            params={"ticker": ticker}
        )
    if df.empty:
        return []
    df["date"] = df["date"].astype(str)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    return df.to_dict(orient="records")


# Simple test runner
if __name__ == "__main__":
    print("Testing get_ticker_detail_rows...")
    try:
        rows = get_ticker_detail_rows("AAPL")
        print(f"Found {len(rows)} rows for AAPL")
        if rows:
            print("First row:", rows[0])
        else:
            print("No data found for AAPL")
    except Exception as e:
        print("Error:", str(e))

    # Add more calls...
    # rows_msft = get_ticker_detail_rows("MSFT")
    # ...