#!/usr/bin/env python
"""Check parsed output"""
import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

with open('Absa.pdf', 'rb') as f:
    csv_bytes, year, note = pdf_to_csv_bytes(f.read())

csv_text = csv_bytes.decode('utf-8')
df = pd.read_csv(StringIO(csv_text))

print(f"Total transactions: {len(df)}")
print()
print("Last 10 transactions:")
for idx, row in df.tail(10).iterrows():
    print(f"{row['date']} | {row['description']:40} | {row['amount']:>15,.2f}")

print()
total = df['amount'].sum()
print(f"NET TOTAL: R {total:,.2f}")
