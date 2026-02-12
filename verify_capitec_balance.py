#!/usr/bin/env python3
"""
Verify data integrity by checking balance calculations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd

csv_path = os.path.join(os.path.dirname(__file__), 'Bank_statements', 'account_statement_1-Feb-2025_to_8-Feb-2026.csv')

# Read raw CSV to check balance column
df = pd.read_csv(csv_path)

print("Balance Verification")
print("=" * 80)

# Get first and last balances
first_balance = df['Balance'].iloc[0]
last_balance = df['Balance'].iloc[-1]

print(f"\nFirst transaction balance: R{first_balance}")
print(f"Last transaction balance: R{last_balance}")
print(f"Balance change: R{last_balance - first_balance}")

# Check if we have any transactions row 2 to verify
print(f"\nFirst few rows:")
for idx, row in df.head(3).iterrows():
    money_in = row['Money In'] if pd.notna(row['Money In']) else 0
    money_out = row['Money Out'] if pd.notna(row['Money Out']) else 0
    fee = row['Fee'] if pd.notna(row['Fee']) else 0
    balance = row['Balance']
    
    net_txn = money_in + money_out + fee
    print(f"  Row {idx+1}: In={money_in:>7} Out={money_out:>7} Fee={fee:>6} Net={net_txn:>7} → Balance {balance}")

print(f"\nTotal rows: {len(df)}")
print(f"Non-NaN Money In count: {df['Money In'].notna().sum()}")
print(f"Non-NaN Money Out count: {df['Money Out'].notna().sum()}")
print(f"Non-NaN Fee count: {df['Fee'].notna().sum()}")
