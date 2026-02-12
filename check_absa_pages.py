#!/usr/bin/env python
"""Check ABSA multi-page extraction"""
import sys
sys.path.insert(0, 'backend')
from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

with open('Absa.pdf', 'rb') as f:
    csv_bytes, year = pdf_to_csv_bytes(f.read())

csv_text = csv_bytes.decode('utf-8')
df = pd.read_csv(StringIO(csv_text))

print(f'Total transactions: {len(df)}')
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print()
print('All transactions:')
for idx, row in df.iterrows():
    print(f'{row["date"]} | {row["description"][:50]:50s} | {row["amount"]}')
