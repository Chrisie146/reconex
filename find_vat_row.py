#!/usr/bin/env python
"""Find the problematic VAT line"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

pdf_path = '20260119115115880.pdf'

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, year, detected_bank = pdf_to_csv_bytes(pdf_content)
csv_text = csv_bytes.decode('utf-8')

df = pd.read_csv(StringIO(csv_text))

# Find row 2
if len(df) >= 2:
    row = df.iloc[1]  # Row 2 (0-indexed)
    print(f"Row 2:")
    print(f"  Date: '{row['date']}'")
    print(f"  Description: '{row['description']}'")
    print(f"  Amount: '{row['amount']}'")
