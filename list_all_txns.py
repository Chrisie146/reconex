#!/usr/bin/env python
"""List all normalized transactions"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.pdf_parser import pdf_to_csv_bytes
from services.parser import normalize_csv
from io import StringIO

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, year, detected_bank = pdf_to_csv_bytes(pdf_content)
normalized, _, _, _ = normalize_csv(csv_bytes, year, detected_bank)

print("All 44 normalized transactions:")
print("="*80)
income_total = 0
expense_total = 0

for i, txn in enumerate(normalized):
    sign = "+" if txn['amount'] > 0 else " "
    print(f"{i+1:2d}. {txn['date']} | {sign}{txn['amount']:8.2f} | {txn['description'][:50]}")
    if txn['amount'] > 0:
        income_total += txn['amount']
    else:
        expense_total += txn['amount']

print("="*80)
print(f"Income total:   {income_total:10.2f}")
print(f"Expense total:  {expense_total:10.2f}")
print(f"Net:            {income_total + expense_total:10.2f}")
print(f"Expected:       {-12675.47:10.2f}")
print(f"Missing:        {(income_total + expense_total) - (-12675.47):10.2f}")
