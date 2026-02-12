#!/usr/bin/env python3
"""
Show which parsed transactions don't match PDF rows
"""
import sys
sys.path.insert(0, 'backend')

from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

pdf_path = "Capitec.pdf"

# Get parsed data
with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, _ = pdf_to_csv_bytes(pdf_content)
df = pd.read_csv(io.BytesIO(csv_bytes))

# Show the extra/mismatched transactions
problem_dates = ['11/01/2026', '19/12/2025', '20/10/2025', '24/11/2025']

for date in problem_dates:
    matching = df[df['date'] == date]
    if len(matching) > 0:
        print(f"\n{date} ({len(matching)} rows parsed):")
        for idx, row in matching.iterrows():
            print(f"  - {row['description'][:60]:<60} | {row['amount']}")
