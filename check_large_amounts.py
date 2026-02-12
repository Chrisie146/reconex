#!/usr/bin/env python3
"""
Check what transactions have large amounts (> 1000) to verify they're real
"""
import sys
sys.path.insert(0, 'backend')

from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io
import re

pdf_path = "Capitec.pdf"

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, _ = pdf_to_csv_bytes(pdf_content)
df = pd.read_csv(io.BytesIO(csv_bytes))

# Parse amounts
def parse_amount(s):
    if pd.isna(s):
        return None
    s = str(s).strip()
    match = re.search(r'-?\s*[\d\s,]+\.?\d{0,2}', s)
    if match:
        amt_str = match.group(0).replace(' ', '').replace(',', '')
        try:
            return float(amt_str)
        except:
            pass
    return None

df['amount_numeric'] = df['amount'].apply(parse_amount)

# Show large amounts
print("Transactions with amounts > 1000:")
large = df[df['amount_numeric'] > 1000].sort_values('amount_numeric', ascending=False)
for idx, row in large.iterrows():
    print(f"  {row['date']} | {row['description'][:60]:<60} | {row['amount_numeric']:>10}")
