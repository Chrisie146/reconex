#!/usr/bin/env python
"""Test FNB CSV 62514285346.csv and validate net balance"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
from io import StringIO
from services.parser import normalize_csv

# Load CSV file
csv_path = r'Bank_statements\62514285346.csv'

print("="*80)
print(f"Testing FNB CSV: {csv_path}")
print("="*80)

with open(csv_path, 'rb') as f:
    csv_bytes = f.read()

# Parse as bytes
csv_text = csv_bytes.decode('utf-8')
lines = csv_text.split('\n')

print(f"\nFile size: {len(csv_bytes)} bytes")
print(f"Total lines: {len(lines)}")

# Skip header lines and find transaction data
transaction_lines = []
reading_transactions = False
for line in lines:
    # Start reading when we hit the Date column header
    if line.startswith('Date'):
        reading_transactions = True
        continue
    if reading_transactions and line.strip() and not line.startswith(','):
        transaction_lines.append(line)

print(f"Transaction lines found: {len(transaction_lines)}")

# Parse transactions manually to ensure accuracy
print("\n" + "="*80)
print("RAW CALCULATION (from CSV):")
print("="*80)

total_amount = 0.0
total_debits = 0.0
total_credits = 0.0
transaction_count = 0

for i, line in enumerate(transaction_lines, 1):
    parts = line.split(',')
    if len(parts) >= 3:
        try:
            date_str = parts[0].strip()
            amount_str = parts[1].strip()
            balance_str = parts[2].strip()
            description = parts[3].strip() if len(parts) > 3 else ''
            
            # Parse amount (signed: positive = income, negative = expense)
            amount = float(amount_str)
            total_amount += amount
            
            if amount > 0:
                total_credits += amount
            else:
                total_debits += amount
            
            transaction_count += 1
            
            # Show first and last 5 transactions
            if i <= 5 or i > len(transaction_lines) - 5:
                print(f"  {date_str:12} | {amount:>10.2f} | {balance_str:>10} | {description[:40]:40}")
        except ValueError as e:
            if i <= 5:
                print(f"  ERROR parsing line {i}: {line}")

if len(transaction_lines) > 10:
    print(f"  ... ({len(transaction_lines) - 10} more transactions) ...")

print("\n" + "-"*80)
print(f"Total transactions: {transaction_count}")
print(f"Total Credits (income):  R {total_credits:>12,.2f}")
print(f"Total Debits (expenses): R {total_debits:>12,.2f}")
print(f"NET BALANCE:             R {total_amount:>12,.2f}")
print("\nExpected: R       1,564.38")
print("="*80)

# Verify using normalization
print("\nValidating with parser.normalize_csv()...")
try:
    # Need to determine the year
    year = 2026
    
    normalized, msg, skipped = normalize_csv(csv_bytes, year, 'fnb')
    
    if normalized:
        net = sum(t['amount'] for t in normalized)
        print(f"Normalized transactions: {len(normalized)}")
        print(f"Skipped: {len(skipped) if skipped else 0}")
        print(f"Normalized NET: R {net:,.2f}")
    else:
        print(f"Error: {msg}")
except Exception as e:
    print(f"Error during normalization: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
if abs(total_amount - 1564.38) < 0.01:
    print("✓ TEST PASSED: Net balance matches expected R 1,564.38")
else:
    print(f"✗ TEST FAILED: Expected R 1,564.38 but got R {total_amount:,.2f}")
    print(f"  Difference: R {total_amount - 1564.38:,.2f}")
print("="*80)
