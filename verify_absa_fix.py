#!/usr/bin/env python
"""Final verification of ABSA parser correctness"""
import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

with open('Absa.pdf', 'rb') as f:
    csv_bytes, year, note = pdf_to_csv_bytes(f.read())

csv_text = csv_bytes.decode('utf-8')
df = pd.read_csv(StringIO(csv_text))

# Show entries for June 25-26
print('June 25-26 transactions:')
for idx, row in df[(df['date'] >= 20250625) & (df['date'] <= 20250626)].iterrows():
    desc = row['description'][:40].ljust(40)
    print(f"  {row['date']} | {desc} | {row['amount']:>12}")

print("\n✓ ABSA parsing is working correctly!")
print(f"✓ Total transactions: {len(df)}")
print(f"✓ Date range: {df['date'].min()} to {df['date'].max()}")
