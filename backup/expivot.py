import pandas as pd

# Configurable variables at the top
file_path = 'wht.xlsx'  # Replace with your actual Excel file path
key_column = 'ticker'  # The column to group by and merge on (from your pivot rows)
amount_column = 'amount'  # The main numeric column to aggregate
item_type_column = 'item type'  # The column to pivot on for different categories (if present)
drop_unnamed = True  # Whether to drop unnamed/empty columns

# Define calculated fields as lambdas (adjust based on your actual pivoted columns)
# Example assumptions: pivoted columns might include 'dividend', 'withholding', 'refund' (lowercase or as in data)
# Update keys to match actual item types after running and seeing output
item_type_mapping = {
    'dividend': 'Gross Dividend',
    'withholding': 'WHT',
    'refund': 'Total WHT Refunded'  # Change 'refund' to actual item type for refunds
}
calculated_fields = [  # List of dicts for calculated columns (name, formula as lambda on the pivot DataFrame)
    {'name': 'Net WHT', 'formula': lambda df: df.get('WHT', 0) + df.get('Total WHT Refunded', 0)},
    {'name': 'Final Amount', 'formula': lambda df: df.get('Gross Dividend', 0) + df.get('Net WHT', 0)},
    {'name': 'WHT Refund %', 'formula': lambda df: (df.get('Total WHT Refunded', 0) / -df.get('WHT', 0)) * 100 if 'WHT' in df.columns and df['WHT'].ne(0).any() else None},
    {'name': 'Final Amount %', 'formula': lambda df: (df['Final Amount'] / df.get('Gross Dividend', 0)) * 100 if 'Gross Dividend' in df.columns and df['Gross Dividend'].ne(0).any() else None}
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

# Identify relevant DataFrames (those containing the key_column)
relevant_dfs = {name: df for name, df in dfs.items() if key_column in df.columns}

if not relevant_dfs:
    raise ValueError(f"No sheets found containing the '{key_column}' column.")

# Merge relevant DataFrames on the key_column (outer join to preserve data)
from functools import reduce
df_list = list(relevant_dfs.values())
df_merged = reduce(lambda left, right: pd.merge(left, right, on=key_column, how='outer'), df_list)

# Print available columns for debugging
print("\nAvailable columns in merged DataFrame:")
print(df_merged.columns.tolist())

# Drop unnamed columns if requested (e.g., if all NaN or empty)
if drop_unnamed:
    unnamed_cols = [col for col in df_merged.columns if 'Unnamed' in str(col)]
    for col in unnamed_cols:
        if df_merged[col].isna().all():
            df_merged.drop(col, axis=1, inplace=True)
            print(f"Dropped empty column: {col}")

# Check for required columns
required_cols = [key_column]
if amount_column not in df_merged.columns:
    raise ValueError(f"Missing '{amount_column}' column in merged data.")
required_cols.append(amount_column)

# Print unique item types if the column exists
if item_type_column in df_merged.columns:
    unique_types = df_merged[item_type_column].unique()
    print(f"\nUnique values in '{item_type_column}': {unique_types}")
    print("Update 'item_type_mapping' in the script to match these for accurate renaming.")

# Create the pivot: If item_type_column exists, pivot on it; else, just groupby sum
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

# Rename columns based on mapping (if pivoted)
if item_type_column in df_merged.columns:
    pivot.rename(columns=item_type_mapping, inplace=True)

# Add calculated fields
for calc in calculated_fields:
    result = calc['formula'](pivot)
    if result is not None:
        pivot[calc['name']] = result
    else:
        print(f"Warning: Skipping '{calc['name']}' due to missing required columns or division by zero.")

# Handle potential NaN
pivot = pivot.fillna(0)

# Output the result
print("\nPivot Table Result:")
print(pivot)