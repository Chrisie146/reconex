#!/usr/bin/env python3
"""
Check if any parsed amounts look like balance values (>1000 for non-income transactions)
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

# Look for suspicious amounts (those that look like they might be balance values)
suspicious = df[(df['amount_numeric'].abs() > 1000) & (~df['description'].str.contains('Payment Received|Salary|Anpersald|salary', case=False, na=False))]

if len(suspicious) > 0:
    print(f"⚠ Found {len(suspicious)} suspicious amounts (>1000, not deposits):")
    for idx, row in suspicious.iterrows():
        print(f"  {row['date']} | {row['description'][:50]:<50} | {row['amount_numeric']}")
else:
    print("✅ All amounts look correct - no balance values being used as transactions")

print(f"\nTotal transactions: {len(df)}")
print(f"Negative: {(df['amount_numeric'] < 0).sum()}")
print(f"Positive: {(df['amount_numeric'] > 0).sum()}")
