#!/usr/bin/env python
"""Verify that other bank parsers still work"""
import sys
import os
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

# Test files to check
test_files = [
    'Absa.pdf',
    'Capitec.pdf',
    'FNB_ASPIRE_CURRENT_ACCOUNT_132.pdf',
    'FNB_PREMIER_CURRENT_ACCOUNT_164.pdf'
]

print('='*70)
print('TESTING OTHER BANK PARSERS')
print('='*70)

for filename in test_files:
    if not os.path.exists(filename):
        print(f'\n[SKIP] {filename} - File not found')
        continue
    
    try:
        print(f'\n[TEST] {filename}')
        with open(filename, 'rb') as f:
            csv_bytes, year, note = pdf_to_csv_bytes(f.read())
        
        csv_text = csv_bytes.decode('utf-8')
        df = pd.read_csv(StringIO(csv_text))
        
        total = len(df)
        expenses = len(df[df["amount"] < 0])
        income = len(df[df["amount"] > 0])
        net = df["amount"].sum()
        
        print(f'  [OK] Total: {total}, Expenses: {expenses}, Income: {income}')
        print(f'  [OK] Net: R {net:,.2f}')
        
        # Sanity check: should have both income and expenses (unless it's a special case)
        if total > 50 and (income == 0 or expenses == 0):
            print(f'  [WARN] Only {income} income and {expenses} expenses')
        
    except Exception as e:
        print(f'  [ERROR] {e}')

print('\n' + '='*70)
print('VERIFICATION COMPLETE')
print('='*70)
