import pandas as pd

# Configurable variables at the top
file_path = 'wht.xlsx'  # Replace with your actual Excel file path
key_column = 'ticker'  # The column to group by and merge on
amount_column = 'amount'  # The main numeric column to aggregate
item_type_column = 'item type'  # The column to pivot on for categories
drop_unnamed = True  # Whether to drop unnamed/empty columns
refund_sheets_keywords = ['wht', 'refund']  # Keywords to identify potential refund sheets
refund_tickers = ['SCHO', 'TLT', 'XHLF', 'XONE', 'SGOV']  # Tickers eligible for 100% refund (if no data)

# Updated mapping to match your data's item types
item_type_mapping = {
    'Dividends': 'Total Dividends',
    'Withholding Tax': 'Total WHT Paid'
}

# Calculated fields (adjusted for signs: WHT Paid will be made positive)
calculated_fields = [
    {'name': 'Net WHT', 'formula': lambda df: -df.get('Total WHT Paid', 0) + df.get('Total WHT Refunded', 0)},
    {'name': 'Final Amount', 'formula': lambda df: df.get('Total Dividends', 0) + df['Net WHT']},
    {'name': 'WHT Refund %', 'formula': lambda df: (df.get('Total WHT Refunded', 0) / df.get('Total WHT Paid', 0)) * 100 if 'Total WHT Paid' in df.columns and df['Total WHT Paid'].ne(0).any() else None},
    {'name': 'Final Amount %', 'formula': lambda df: (df['Final Amount'] / df.get('Total Dividends', 0)) * 100 if 'Total Dividends' in df.columns and df['Total Dividends'].ne(0).any() else None}
]

# Load the Excel file
excel = pd.ExcelFile(file_path)

# Get all sheet names
sheet_names = excel.sheet_names

# Load all sheets into a dictionary of DataFrames
dfs = {}
for sheet in sheet_names:
    try:
        dfs[sheet] = pd.read_excel(excel, sheet_name=sheet)
        print(f"Loaded sheet: {sheet}")
    except Exception as e:
        print(f"Skipping sheet {sheet}: {e}")

# Print detailed info for EACH sheet
for name, df in dfs.items():
    print(f"\nSheet '{name}' details:")
    print(f"Columns: {df.columns.tolist()}")
    if item_type_column in df.columns:
        unique_types = df[item_type_column].unique()
        print(f"Unique '{item_type_column}': {unique_types}")
    print("Sample data (first 5 rows):")
    print(df.head(5))
    print("-" * 50)

# Identify relevant DataFrames for main data (those with key_column)
relevant_dfs = {name: df for name, df in dfs.items() if key_column in df.columns}

if not relevant_dfs:
    raise ValueError(f"No sheets found containing the '{key_column}' column.")

# Merge relevant DataFrames on the key_column
from functools import reduce
df_list = list(relevant_dfs.values())
df_merged = reduce(lambda left, right: pd.merge(left, right, on=key_column, how='outer'), df_list)

# Print available columns in merged DataFrame
print("\nAvailable columns in merged DataFrame:")
print(df_merged.columns.tolist())

# Drop unnamed columns if requested
if drop_unnamed:
    unnamed_cols = [col for col in df_merged.columns if 'Unnamed' in str(col)]
    for col in unnamed_cols:
        if df_merged[col].isna().all():
            df_merged.drop(col, axis=1, inplace=True)
            print(f"Dropped empty column: {col}")

# Create the pivot
if item_type_column in df_merged.columns:
    pivot = pd.pivot_table(
        df_merged,
        index=key_column,
        columns=item_type_column,
        values=amount_column,
        aggfunc='sum',
        fill_value=0
    ).reset_index()
else:
    print(f"\nNo '{item_type_column}' column found; falling back to simple sum of '{amount_column}' by '{key_column}'.")
    pivot = df_merged.groupby(key_column)[amount_column].sum().reset_index()
    pivot.columns = [key_column, f'Total {amount_column.capitalize()}']

# Rename columns based on mapping
pivot.rename(columns=item_type_mapping, inplace=True)

# Make Total WHT Paid positive (to match Excel picture)
if 'Total WHT Paid' in pivot.columns:
    pivot['Total WHT Paid'] = -pivot['Total WHT Paid']  # Flip sign from negative to positive

# Look for and merge refund data from sheets matching keywords
refund_added = False
for sheet_name, df in dfs.items():
    if any(keyword.lower() in sheet_name.lower() for keyword in refund_sheets_keywords):
        if key_column in df.columns and amount_column in df.columns:
            refund_pivot = df.groupby(key_column)[amount_column].sum().reset_index()
            refund_pivot.columns = [key_column, 'Total WHT Refunded']
            pivot = pd.merge(pivot, refund_pivot, on=key_column, how='left').fillna(0)
            print(f"Added refunds from sheet '{sheet_name}' as 'Total WHT Refunded'.")
            refund_added = True
            break  # Assume only one refund sheet

# If no refund data found, optionally apply rule-based 100% refund for specific tickers
if not refund_added:
    print("No refund sheet found. Applying rule-based 100% refund for eligible tickers.")
    if 'Total WHT Paid' in pivot.columns:
        pivot['Total WHT Refunded'] = 0
        pivot.loc[pivot[key_column].isin(refund_tickers), 'Total WHT Refunded'] = pivot['Total WHT Paid']

# Add calculated fields
for calc in calculated_fields:
    result = calc['formula'](pivot)
    if result is not None:
        pivot[calc['name']] = result
    else:
        print(f"Warning: Skipping '{calc['name']}' due to missing required columns or division by zero.")

# Handle NaN and sort by ticker
pivot = pivot.fillna(0).sort_values(by=key_column)

# Add grand total row
grand_total = pivot.select_dtypes(include='number').sum()
grand_total[key_column] = 'Grand Total'
pivot = pd.concat([pivot, pd.DataFrame([grand_total])], ignore_index=True)

# Output the result
print("\nPivot Table Result:")
print(pivot)