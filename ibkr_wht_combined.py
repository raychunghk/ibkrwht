#!/usr/bin/env python3
"""
Combined IBKR Dividend and WHT Report Generator

This script combines the functionality of ibkrtxfcsv.py and whtreport.py:
1. Processes IBKR CSV activity statements
2. Stores transactions in MariaDB
3. Generates dividend and WHT reports from database data

Usage:
    python ibkr_wht_combined.py --csv <csv_file_path>
    python ibkr_wht_combined.py --report
    python ibkr_wht_combined.py --csv <csv_file_path> --report
"""

import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
import sys
import argparse
from datetime import date

# Database configuration
DB_CONFIG = {
    'host': '192.168.0.129',
    'user': 'root',
    'password': 'pwd 230479',
    'database': 'ibkr_wht',
    'port': 3306
}

# Default paths
DEFAULT_CSV_PATH = './U8485385_U8485385_20250220_20260220_AS_1896658_c85a157a0d6dcececc1c040b5f3d7408.csv'
OUTPUT_EXCEL_PATH = 'dividend_report.xlsx'


def get_db_connection():
    """Create and return a database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MariaDB: {e}")
        sys.exit(1)


def insert_transactions(df):
    """Insert transaction data into the database, skipping duplicates."""
    connection = get_db_connection()
    cursor = connection.cursor()

    insert_query = """
        INSERT IGNORE INTO transactions 
        (item_type, currency, date, ticker, detail, amount)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    records = []
    for _, row in df.iterrows():
        records.append((
            row['item type'],
            row['currency'],
            row['date'],
            row['ticker'],
            row['detail'],
            row['amount']
        ))

    try:
        cursor.executemany(insert_query, records)
        connection.commit()
        inserted = cursor.rowcount
        skipped = len(records) - inserted
        print(f"Successfully inserted {inserted} records ({skipped} duplicates skipped).")
    except Error as e:
        print(f"Error inserting records: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()


def extract_ticker(desc):
    """Extract ticker symbol from description."""
    if pd.isna(desc):
        return ""
    if "(" in desc:
        return desc.split("(")[0].strip()
    return desc.split(" ")[0].strip()


def process_csv(csv_file_path):
    """Process IBKR CSV and store data in MariaDB."""
    print(f"Processing CSV file: {csv_file_path}")
    
    # Read the CSV file, skipping header rows
    df = pd.read_csv(csv_file_path, skip_blank_lines=True, skiprows=7)
    
    # Filter for only 'Dividends' and 'Withholding Tax' in the first column
    # Filter for only 'USD' in the Currency column
    # Ignore rows where the 'Date' column is 'Total' or NaN
    mask = (
        (df.iloc[:, 0].isin(['Dividends', 'Withholding Tax'])) & 
        (df.iloc[:, 2] == 'USD') & 
        (df.iloc[:, 3] != 'Total') &
        (df.iloc[:, 3].notna())
    )
    
    filtered_df = df[mask].copy()
    
    # Rename columns based on IBKR's standard CSV header positions
    filtered_df = filtered_df.iloc[:, [0, 2, 3, 4, 5]]
    filtered_df.columns = ['item type', 'currency', 'date', 'description', 'amount']
    
    # Apply transformations
    filtered_df['ticker'] = filtered_df['description'].apply(extract_ticker)
    filtered_df['amount'] = pd.to_numeric(filtered_df['amount'], errors='coerce')
    
    # Reorder columns to match schema
    final_df = filtered_df[['item type', 'currency', 'date', 'ticker', 'description', 'amount']]
    final_df = final_df.rename(columns={'description': 'detail'})
    
    # Convert date column to proper format
    final_df['date'] = pd.to_datetime(final_df['date'], errors='coerce').dt.date
    
    print(f"Found {len(final_df)} records to process:")
    print(f"  - Dividends: {len(final_df[final_df['item type'] == 'Dividends'])}")
    print(f"  - Withholding Tax: {len(final_df[final_df['item type'] == 'Withholding Tax'])}")
    
    # Insert into database
    insert_transactions(final_df)
    
    return final_df


def load_transactions_from_db():
    """Load all transactions from the database."""
    connection = get_db_connection()
    
    query = """
        SELECT 
            item_type,
            currency,
            date,
            ticker,
            detail,
            amount
        FROM transactions
        WHERE currency = 'USD'
        ORDER BY date, ticker
    """
    
    try:
        df = pd.read_sql(query, connection)
        print(f"Loaded {len(df)} transactions from database.")
        return df
    except Error as e:
        print(f"Error loading transactions: {e}")
        return None
    finally:
        connection.close()


def load_wht_transactions_from_db():
    """Load only Withholding Tax transactions from the database."""
    connection = get_db_connection()
    
    query = """
        SELECT 
            item_type,
            currency,
            date,
            ticker,
            detail,
            amount
        FROM transactions
        WHERE currency = 'USD' 
          AND item_type = 'Withholding Tax'
        ORDER BY date, ticker
    """
    
    try:
        df = pd.read_sql(query, connection)
        return df
    except Error as e:
        print(f"Error loading WHT transactions: {e}")
        return None
    finally:
        connection.close()


def save_report_to_db(report_df):
    """Save the generated report to the database."""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Clear previous reports
    cursor.execute("DELETE FROM dividend_reports")
    
    insert_query = """
        INSERT INTO dividend_reports 
        (report_date, ticker, total_dividends, total_wht_paid, total_wht_refunded,
         net_wht, final_amount, wht_refund_pct, final_amount_pct)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    report_date = date.today()
    records = []
    
    for _, row in report_df.iterrows():
        if row['SYMBOL'] != 'Grand Total':
            records.append((
                report_date,
                row['SYMBOL'],
                row['Total Dividends'],
                row['Total WHT Paid'],
                row['Total WHT Refunded'],
                row['Net WHT'],
                row['Final Amount'],
                row['WHT Refund %'],
                row['Final Amount %']
            ))
    
    try:
        if records:
            cursor.executemany(insert_query, records)
            connection.commit()
            print(f"Saved {cursor.rowcount} report records to database.")
    except Error as e:
        print(f"Error saving report: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()


def generate_dividend_report():
    """
    Loads data from the database, processes dividend and withholding tax
    transactions, calculates refunds, and generates a summary report.
    """
    # Load all transactions from database
    combined_df = load_transactions_from_db()
    
    if combined_df is None or combined_df.empty:
        print("Error: No data could be loaded from the database.")
        return None, None
    
    # Standardize column names
    combined_df.columns = [col.lower().strip() for col in combined_df.columns]
    
    # Rename item_type to item type for consistency
    if 'item_type' in combined_df.columns:
        combined_df = combined_df.rename(columns={'item_type': 'item type'})
    
    # Ensure 'amount' is numeric
    combined_df['amount'] = pd.to_numeric(combined_df['amount'], errors='coerce')
    combined_df.dropna(subset=['ticker', 'amount'], inplace=True)
    
    # Get USD tickers from WHT transactions for filtering
    wht_df = load_wht_transactions_from_db()
    TICKERS_TO_PROCESS = []
    
    if wht_df is not None and not wht_df.empty:
        TICKERS_TO_PROCESS = wht_df['ticker'].unique().tolist()
        print(f"Found {len(TICKERS_TO_PROCESS)} tickers to process: {', '.join(TICKERS_TO_PROCESS)}")
        combined_df = combined_df[combined_df['ticker'].isin(TICKERS_TO_PROCESS)].copy()
    else:
        print("Warning: No WHT transactions found. The report will be empty.")
        combined_df = combined_df.iloc[0:0]
    
    if combined_df.empty:
        print("Error: No data to process after filtering. Exiting.")
        return None, None
    
    # Calculate Core Aggregations
    report = combined_df.groupby('ticker').apply(lambda x: pd.Series({
        'Total Dividends': x.loc[x['item type'] == 'Dividends', 'amount'].sum()
    })).reset_index()
    
    # Calculate WHT Paid and Refunded
    wht_paid = pd.Series(dtype=float)
    wht_refunded = pd.Series(dtype=float)
    
    if wht_df is not None and not wht_df.empty:
        print("\nCalculating WHT Paid and Refunded from database...")
        
        wht_df['amount'] = pd.to_numeric(wht_df['amount'], errors='coerce')
        
        wht_paid_transactions = wht_df[wht_df['amount'] < 0].copy()
        wht_paid = wht_paid_transactions.groupby('ticker')['amount'].sum().abs().rename('Total WHT Paid')
        
        wht_refund_transactions = wht_df[wht_df['amount'] > 0].copy()
        wht_refunded = wht_refund_transactions.groupby('ticker')['amount'].sum().rename('Total WHT Refunded')
    
    report = report.merge(wht_paid, on='ticker', how='left')
    report = report.merge(wht_refunded, on='ticker', how='left')
    
    report['Total WHT Paid'].fillna(0, inplace=True)
    report['Total WHT Refunded'].fillna(0, inplace=True)
    report.fillna(0, inplace=True)
    
    # Calculate Derived and Percentage Columns
    report['Net WHT'] = report['Total WHT Paid'] - report['Total WHT Refunded']
    report['Final Amount'] = report['Total Dividends'] - report['Net WHT']
    
    report['WHT Refund %'] = np.where(
        report['Total WHT Paid'] > 0,
        (report['Total WHT Refunded'] / report['Total WHT Paid']) * 100,
        0
    )
    report['Final Amount %'] = np.where(
        report['Total Dividends'] > 0,
        (report['Final Amount'] / report['Total Dividends']) * 100,
        0
    )
    
    # Add Grand Total Row
    if not report.empty:
        total_dividends = report['Total Dividends'].sum()
        total_wht_paid = report['Total WHT Paid'].sum()
        total_wht_refunded = report['Total WHT Refunded'].sum()
        
        net_wht_total = total_wht_paid - total_wht_refunded
        overall_refund_pct = (total_wht_refunded / total_wht_paid) * 100 if total_wht_paid > 0 else 0
        overall_final_pct = ((total_dividends - net_wht_total) / total_dividends) * 100 if total_dividends > 0 else 0
        
        grand_total = pd.DataFrame({
            'ticker': ['Grand Total'],
            'Total Dividends': [total_dividends],
            'Total WHT Paid': [total_wht_paid],
            'Total WHT Refunded': [total_wht_refunded],
            'Net WHT': [net_wht_total],
            'Final Amount': [total_dividends - net_wht_total],
            'WHT Refund %': [overall_refund_pct],
            'Final Amount %': [overall_final_pct]
        })
        report = pd.concat([report, grand_total], ignore_index=True)
    
    # Final Formatting and Sorting
    if 'Grand Total' in report['ticker'].values:
        grand_total_row = report[report['ticker'] == 'Grand Total']
        data_rows = report[report['ticker'] != 'Grand Total'].sort_values('ticker').reset_index(drop=True)
        report = pd.concat([data_rows, grand_total_row], ignore_index=True)
    else:
        report = report.sort_values('ticker').reset_index(drop=True)
    
    report.rename(columns={'ticker': 'SYMBOL'}, inplace=True)
    
    # Create formatted version
    formatted_report = report.copy()
    numeric_cols = ['Total Dividends', 'Total WHT Paid', 'Total WHT Refunded', 'Net WHT', 'Final Amount']
    percent_cols = ['WHT Refund %', 'Final Amount %']
    
    for col in numeric_cols:
        formatted_report[col] = formatted_report[col].map('{:,.2f}'.format)
    for col in percent_cols:
        formatted_report[col] = formatted_report[col].map('{:.2f}%'.format)
    
    return report, formatted_report


def display_and_save_report(raw_report, formatted_report):
    """Display the report and save to Excel and database."""
    if formatted_report is None:
        return
    
    # Output Results
    print("\n" + "="*80)
    print(" " * 30 + "DIVIDEND & WHT REPORT")
    print("="*80)
    
    # Print to console
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
        print(formatted_report)
    
    # Save to Excel
    try:
        with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine='openpyxl') as writer:
            formatted_report.to_excel(writer, sheet_name='Report', index=False)
            raw_report.to_excel(writer, sheet_name='Raw_Data_Report', index=False)
        print(f"\nReport successfully saved to '{OUTPUT_EXCEL_PATH}'")
    except Exception as e:
        print(f"\nError: Failed to save the report to Excel. {e}")
    
    # Save to database
    save_report_to_db(raw_report)


def main():
    parser = argparse.ArgumentParser(
        description='IBKR Dividend and WHT Report Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ibkr_wht_combined.py --csv ./statement.csv    Process CSV and store in DB
  python ibkr_wht_combined.py --report                  Generate report from DB
  python ibkr_wht_combined.py --csv ./stmt.csv --report Process CSV and generate report
        """
    )
    
    parser.add_argument('--csv', type=str, default=DEFAULT_CSV_PATH,
                        help='Path to IBKR CSV statement file')
    parser.add_argument('--report', action='store_true',
                        help='Generate dividend and WHT report from database')
    
    args = parser.parse_args()
    
    if not args.report and args.csv == DEFAULT_CSV_PATH:
        # No arguments provided, show help
        parser.print_help()
        sys.exit(0)
    
    # Process CSV if requested
    if args.csv:
        try:
            process_csv(args.csv)
            print("\nCSV processing complete! Data stored in MariaDB database 'ibkr_wht'.")
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            sys.exit(1)
    
    # Generate report if requested
    if args.report:
        print("\n--- Generating Dividend and WHT Report ---")
        raw_report, formatted_report = generate_dividend_report()
        display_and_save_report(raw_report, formatted_report)


if __name__ == "__main__":
    main()
