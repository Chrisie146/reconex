#!/usr/bin/env python3
"""
Check how many 19/12 transactions we have in parsed CSV
"""
import sys
sys.path.insert(0, 'backend')

from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

pdf_path = "Capitec.pdf"

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, _ = pdf_to_csv_bytes(pdf_content)
df = pd.read_csv(io.BytesIO(csv_bytes))

# Find 19/12 rows
rows_1912 = df[df['date'] == '19/12/2025']
print(f"Transactions on 19/12/2025: {len(rows_1912)}")
for idx, row in rows_1912.iterrows():
    print(f"  - {row['description'][:50]:<50} | {row['amount']:>10}")
