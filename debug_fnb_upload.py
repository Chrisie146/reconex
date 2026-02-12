#!/usr/bin/env python
"""Debug FNB CSV processing - compare raw vs upload"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
from io import StringIO
from services.parser import normalize_csv
from services.bank_adapters import FNBAdapter

csv_path = r'Bank_statements\62514285346.csv'

print("="*80)
print("DETAILED DEBUG: FNB CSV Processing")
print("="*80)

with open(csv_path, 'rb') as f:
    csv_bytes = f.read()

# First: Raw CSV calculation
print("\n[STEP 1] RAW CSV CALCULATION")
print("-"*80)

csv_text = csv_bytes.decode('utf-8')
df_raw = pd.read_csv(StringIO(csv_text), skiprows=6)  # Skip header rows

print(f"Columns found: {list(df_raw.columns)}")
print(f"Total rows: {len(df_raw)}")

# Clean nan rows
df_raw = df_raw.dropna(subset=['Date'])

# Handle column name variations (may have leading spaces)
amount_col = ' Amount' if ' Amount' in df_raw.columns else 'Amount'
balance_col = ' Balance' if ' Balance' in df_raw.columns else 'Balance'
date_col = 'Date'

df_raw[amount_col] = pd.to_numeric(df_raw[amount_col], errors='coerce')

raw_net = df_raw[amount_col].sum()
print(f"Raw CSV Net: R {raw_net:,.2f}")

print("\nFirst 5 rows:")
for idx, row in df_raw.head(5).iterrows():
    print(f"  {row[date_col]} | {row[amount_col]:>10.2f} | Bal: {row[balance_col]:>10}")

# Second: normalize_csv result
print("\n[STEP 2] NORMALIZE_CSV RESULT")
print("-"*80)

normalized, msg, skipped, bank = normalize_csv(csv_bytes, statement_year=2026, forced_bank='fnb')

if normalized:
    norm_net = sum(t['amount'] for t in normalized)
    print(f"Normalized transactions: {len(normalized)}")
    print(f"Normalized Net: R {norm_net:,.2f}")
    
    print("\nFirst 5 normalized:")
    for i, txn in enumerate(normalized[:5]):
        print(f"  {txn['date']} | {txn['amount']:>10.2f} | {txn['description'][:40]}")
    
    print(f"\nValidation metadata:")
    for i, txn in enumerate(normalized[:5]):
        print(f"  {i}: verified={txn.get('balance_verified')}, diff={txn.get('balance_difference')}, msg={txn.get('validation_message', '')[:50]}")
else:
    print(f"Error: {msg}")

# Third: Check adapter directly
print("\n[STEP 3] DIRECT ADAPTER PROCESSING")
print("-"*80)

from services.parser import _find_data_start, _clean_dataframe
df_adapter = _find_data_start(csv_bytes)
df_adapter = _clean_dataframe(df_adapter)

print(f"Adapter input columns: {list(df_adapter.columns)}")
print(f"Adapter input rows: {len(df_adapter)}")

adapter = FNBAdapter()
df_normalized = adapter.normalize(df_adapter, strict=False)

print(f"\nAdapter output columns: {list(df_normalized.columns)}")
print(f"Adapter output rows: {len(df_normalized)}")

if not df_normalized.empty:
    adapter_net = df_normalized['Amount'].sum()
    print(f"Adapter Net Amount: R {adapter_net:,.2f}")
    
    print("\nAdapter validation metadata (first 10 rows):")
    has_corrections = False
    for idx, row in df_normalized.head(10).iterrows():
        val_msg = row.get('validation_message', '')
        verified = row.get('balance_verified')
        if 'corrected' in val_msg.lower():
            has_corrections = True
            print(f"  Row {idx}: *** {row['Amount']:>10.2f} | {val_msg[:60]}")
        else:
            print(f"  Row {idx}: {row['Amount']:>10.2f} | verified={verified}, {val_msg[:50]}")
    
    # Check if any amounts have been corrected
    print("\nChecking for amount corrections...")
    for idx, row in df_normalized.iterrows():
        if 'corrected' in str(row.get('validation_message', '')).lower():
            print(f"  Row {idx}: {row['validation_message']}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Expected:          R  1,564.38")
print(f"Raw CSV:           R {raw_net:>10,.2f}")
if normalized:
    print(f"Normalized:        R {norm_net:>10,.2f}")
if not df_normalized.empty:
    print(f"Adapter Direct:    R {adapter_net:>10,.2f}")
    print(f"Upload reports:    R  2,048.36")
print("="*80)
