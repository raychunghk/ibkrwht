import pandas as pd
import numpy as np

# --- Configuration ---
# Path to the source Excel file.
INPUT_EXCEL_PATH = 'wht.xlsx'
# Path for the output report Excel file.
OUTPUT_EXCEL_PATH = 'dividend_report.xlsx'
# Tickers eligible for 100% WHT refund if no explicit refund data is found.
RULE_BASED_REFUND_TICKERS = ['SCHO', 'TLT', 'XHLF', 'XONE', 'SGOV']


def generate_dividend_report(file_path):
    """
    Loads data from a multi-sheet Excel file, processes dividend and withholding tax
    transactions, calculates refunds, and generates a summary report.

    Args:
        file_path (str): The path to the input Excel file.

    Returns:
        pandas.DataFrame: The final report DataFrame. Returns None if file is not found.
    """
    try:
        excel_file = pd.ExcelFile(file_path)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None

    all_data = []
    sheet_names = excel_file.sheet_names
    print(f"Found sheets: {sheet_names}\n")

    # --- 1. Load and Concatenate Data from All Sheets ---
    for sheet_name in sheet_names:
        print(f"--- Processing sheet: '{sheet_name}' ---")
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            print(f"Columns found: {df.columns.tolist()}")
            print("Sample data:")
            print(df.head(2))
            print("-" * 30)

            # Basic validation: check for essential columns
            required_cols = {'item type', 'ticker', 'amount'}
            if not required_cols.issubset(df.columns):
                print(f"Warning: Sheet '{sheet_name}' is missing one or more required columns ({required_cols}). Skipping.")
                continue

            all_data.append(df)
        except Exception as e:
            print(f"Warning: Could not process sheet '{sheet_name}'. Error: {e}")

    if not all_data:
        print("Error: No valid data could be loaded from any sheet. Exiting.")
        return None

    # Combine all valid sheets into a single DataFrame
    combined_df = pd.concat(all_data, ignore_index=True)

    # --- 2. Data Cleaning and Preparation ---
    # Standardize column names (e.g., handle potential case differences)
    combined_df.columns = [col.lower().strip() for col in combined_df.columns]

    # Ensure 'amount' is numeric, coercing errors to NaN
    combined_df['amount'] = pd.to_numeric(combined_df['amount'], errors='coerce')
    # Drop rows where key data ('ticker', 'amount') is missing
    combined_df.dropna(subset=['ticker', 'amount'], inplace=True)

    # --- TEMP: Filter for only 'USHY' as requested for debugging ---
    print("\nFiltering for ticker 'USHY' as requested...")
    combined_df = combined_df[combined_df['ticker'] == 'USHY'].copy()
    if combined_df.empty:
        print("Error: No data found for ticker 'USHY'. Exiting.")
        return None, None

    # --- 3. Calculate Core Aggregations ---
    # Group by ticker to calculate total dividends and WHT paid.
    # For WHT, we sum first (to account for reversals) and then take the absolute value.
    report = combined_df.groupby('ticker').apply(lambda x: pd.Series({
        'Total Dividends': x.loc[x['item type'] == 'Dividends', 'amount'].sum(),
        'Total WHT Paid': abs(x.loc[x['item type'] == 'Withholding Tax', 'amount'].sum())
    })).reset_index()

    # --- 4. Calculate Refunds ---
    # Identify refund transactions. This assumes refunds are positive amounts in sheets
    # containing 'wht' or 'refund' in their name, and are not 'Dividends'.
    refund_sheets = [s.lower() for s in sheet_names if 'wht' in s.lower() or 'refund' in s.lower()]
    
    # Add a column to track the source sheet for refund identification
    combined_df['sheet_name_source'] = combined_df.apply(lambda row: row.name[0] if isinstance(row.name, tuple) else '', axis=1)

    # Filter for potential refund transactions from the combined data
    refund_transactions = combined_df[
        (combined_df['sheet_name_source'].str.lower().isin(refund_sheets)) &
        (combined_df['item type'] != 'Dividends') &
        (combined_df['amount'] > 0)
    ]
    if not refund_transactions.empty:
        print("\nFound potential refund transactions. Aggregating refunds...")
        explicit_refunds = refund_transactions.groupby('ticker')['amount'].sum().rename('Total WHT Refunded')
        report = report.merge(explicit_refunds, on='ticker', how='left')
    else:
        print("\nNo explicit refund transactions found. Applying rule-based refunds for eligible tickers.")
        report['Total WHT Refunded'] = 0

    # Apply rule-based refunds for specified tickers if they have no explicit refund
    for ticker in RULE_BASED_REFUND_TICKERS:
        # Check if the ticker exists in the report and has no explicit refund calculated
        if ticker in report['ticker'].values and pd.isna(report.loc[report['ticker'] == ticker, 'Total WHT Refunded'].iloc[0]):
            wht_paid = report.loc[report['ticker'] == ticker, 'Total WHT Paid'].iloc[0]
            report.loc[report['ticker'] == ticker, 'Total WHT Refunded'] = wht_paid # 100% refund
            print(f"Applied 100% rule-based refund for ticker: {ticker}")

    # Fill any remaining NaN in refunds with 0
    report['Total WHT Refunded'].fillna(0, inplace=True)

    # --- 5. Calculate Derived and Percentage Columns ---
    report['Net WHT'] = -report['Total WHT Paid'] + report['Total WHT Refunded']
    report['Final Amount'] = report['Total Dividends'] + report['Net WHT']

    # Calculate percentage columns, handling division by zero
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

    # --- 6. Add Grand Total Row ---
    if not report.empty:
        total_dividends = report['Total Dividends'].sum()
        total_wht_paid = report['Total WHT Paid'].sum()
        total_wht_refunded = report['Total WHT Refunded'].sum()
        
        # Calculate overall percentages for the total row
        overall_refund_pct = (total_wht_refunded / total_wht_paid * 100) if total_wht_paid > 0 else 0
        overall_final_pct = ((total_dividends - total_wht_paid + total_wht_refunded) / total_dividends * 100) if total_dividends > 0 else 0

        grand_total = pd.DataFrame({
            'ticker': ['Grand Total'],
            'Total Dividends': [total_dividends],
            'Total WHT Paid': [total_wht_paid],
            'Total WHT Refunded': [total_wht_refunded],
            'Net WHT': [-total_wht_paid + total_wht_refunded],
            'Final Amount': [total_dividends - total_wht_paid + total_wht_refunded],
            'WHT Refund %': [overall_refund_pct],
            'Final Amount %': [overall_final_pct]
        })
        report = pd.concat([report, grand_total], ignore_index=True)

    # --- 7. Final Formatting and Sorting ---
    # Sort by ticker, keeping Grand Total at the bottom
    if 'Grand Total' in report['ticker'].values:
        grand_total_row = report[report['ticker'] == 'Grand Total']
        data_rows = report[report['ticker'] != 'Grand Total'].sort_values('ticker').reset_index(drop=True)
        report = pd.concat([data_rows, grand_total_row], ignore_index=True)
    else:
        report = report.sort_values('ticker').reset_index(drop=True)

    # Rename 'ticker' column for final presentation
    report.rename(columns={'ticker': 'Row Labels'}, inplace=True)

    # Create a formatted version for display and export
    formatted_report = report.copy()
    numeric_cols = ['Total Dividends', 'Total WHT Paid', 'Total WHT Refunded', 'Net WHT', 'Final Amount']
    percent_cols = ['WHT Refund %', 'Final Amount %']

    for col in numeric_cols:
        formatted_report[col] = formatted_report[col].map('{:,.2f}'.format)
    for col in percent_cols:
        formatted_report[col] = formatted_report[col].map('{:.2f}%'.format)

    return report, formatted_report


if __name__ == "__main__":
    # Execute the main logic
    raw_report, final_formatted_report = generate_dividend_report(INPUT_EXCEL_PATH)

    if final_formatted_report is not None:
        # --- 8. Output Results ---
        print("\n" + "="*80)
        print(" " * 30 + "DIVIDEND & WHT REPORT")
        print("="*80)

        # Print the formatted table to the console
        # Using pandas' built-in pretty-print
        with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
            print(final_formatted_report)

        # Save the formatted report to a new Excel file
        try:
            with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine='openpyxl') as writer:
                # Write the formatted data for presentation
                final_formatted_report.to_excel(writer, sheet_name='Report', index=False)
                # Optionally write the raw numeric data to another sheet for further analysis
                raw_report.to_excel(writer, sheet_name='Raw_Data_Report', index=False)
            print(f"\nReport successfully saved to '{OUTPUT_EXCEL_PATH}'")
        except Exception as e:
            print(f"\nError: Failed to save the report to Excel. {e}")
