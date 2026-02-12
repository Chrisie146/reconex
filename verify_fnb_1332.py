#!/usr/bin/env python
"""Verify FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf totals"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.pdf_parser import pdf_to_csv_bytes
from services.parser import normalize_csv
import pandas as pd
from io import StringIO

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'

print("="*80)
print(f"Verifying: {pdf_path}")
print("Expected Net: R 12,675.47")
print("="*80)

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

# Parse PDF
csv_bytes, year, detected_bank = pdf_to_csv_bytes(pdf_content)
print(f"\n[1] PDF Parsing:")
print(f"  Bank: {detected_bank}")
print(f"  Year: {year}")

# Convert to DataFrame
csv_text = csv_bytes.decode('utf-8')
df = pd.read_csv(StringIO(csv_text))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

print(f"\n[2] Raw CSV Stats:")
print(f"  Total rows: {len(df)}")
print(f"  Total credits (income): R {df[df['amount'] > 0]['amount'].sum():,.2f}")
print(f"  Total debits (expenses): R {df[df['amount'] < 0]['amount'].sum():,.2f}")
print(f"  Net amount: R {df['amount'].sum():,.2f}")

# Normalize
normalized, warnings, skipped, bank_source = normalize_csv(csv_bytes, year, detected_bank)

print(f"\n[3] Normalized Transactions:")
print(f"  Count: {len(normalized)}")
if skipped:
    print(f"  Skipped: {len(skipped)}")
if warnings:
    print(f"  Warnings: {warnings[:200]}")

if normalized:
    total_income = sum(t['amount'] for t in normalized if t['amount'] > 0)
    total_expenses = sum(t['amount'] for t in normalized if t['amount'] < 0)
    net = total_income + total_expenses
    
    print(f"\n[4] Financial Summary:")
    print(f"  Total income:   R {total_income:12,.2f}")
    print(f"  Total expenses: R {total_expenses:12,.2f}")
    print(f"  Net:            R {net:12,.2f}")
    print(f"\n  Expected:       R   12,675.47")
    print(f"  Difference:     R {net - 12675.47:12,.2f}")
    
    if abs(net - 12675.47) < 1.0:
        print(f"\n  ✅ NET MATCHES EXPECTED VALUE!")
    else:
        print(f"\n  ⚠ Net differs from expected by R {abs(net - 12675.47):.2f}")

print("\n" + "="*80)
