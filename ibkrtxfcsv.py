import pandas as pd
import mysql.connector
from mysql.connector import Error
import sys

# Database configuration
DB_CONFIG = {
    'host': '192.168.0.129',
    'user': 'root',
    'password': 'pwd 230479',
    'database': 'ibkr_wht',
    'port': 3306
}

# CSV file path - replace with your actual filename
file_path = './U8485385_U8485385_20250220_20260220_AS_1896658_c85a157a0d6dcececc1c040b5f3d7408.csv'


def get_db_connection():
    """Create and return a database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MariaDB: {e}")
        sys.exit(1)


def delete_transactions():
    """Delete all existing transaction records from the database."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM transactions")
        connection.commit()
        print(f"Deleted {cursor.rowcount} existing transaction records.")
    except Error as e:
        print(f"Error deleting records: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()


def insert_transactions(df):
    """Insert transaction data into the database."""
    connection = get_db_connection()
    cursor = connection.cursor()

    insert_query = """
        INSERT INTO transactions 
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
        print(f"Successfully inserted {cursor.rowcount} records.")
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
    # Col 0: Type, Col 2: Currency, Col 3: Date, Col 4: Description, Col 5: Amount
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

    delete_transactions()
    insert_transactions(final_df)
    
    return final_df


if __name__ == "__main__":
    try:
        df = process_csv(file_path)
        print("\nExtraction complete! Data stored in MariaDB database 'ibkr_wht'.")
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)
