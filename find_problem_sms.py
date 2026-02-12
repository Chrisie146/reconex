#!/usr/bin/env python3
"""
Find which parsed row contains the problematic SMS data
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

# Find the problematic row
mask = (df['description'].str.contains('SMS', case=False, na=False)) & (df['amount_numeric'] > 1000)
problem_rows = df[mask]

print(f"Found {len(problem_rows)} SMS rows with amount > 1000:\n")
for idx, row in problem_rows.iterrows():
    print(f"Row {idx}:")
    print(f"  Date: {row['date']}")
    print(f"  Description: {row['description'][:80]}")
    print(f"  Amount (raw): {row['amount']}")
    print(f"  Amount (numeric): {row['amount_numeric']}")
    print()
