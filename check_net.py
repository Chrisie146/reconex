#!/usr/bin/env python
"""Check the NET amount balance"""
import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

with open('Absa.pdf', 'rb') as f:
    csv_bytes, year, note = pdf_to_csv_bytes(f.read())

csv_text = csv_bytes.decode('utf-8')
df = pd.read_csv(StringIO(csv_text))

total_inflows = df[df['amount'] > 0]['amount'].sum()
total_outflows = df[df['amount'] < 0]['amount'].sum()
net = df['amount'].sum()

print(f"Total Inflows:  R {total_inflows:>15,.2f}")
print(f"Total Outflows: R {total_outflows:>15,.2f}")
print(f"NET AMOUNT:     R {net:>15,.2f}")
print()
print("All transactions:")
for idx, row in df.iterrows():
    print(f"{row['date']} | {row['description']:40} | {row['amount']:>15,.2f}")
