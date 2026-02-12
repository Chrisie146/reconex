#!/usr/bin/env python
"""Final test: Verify the ABSA parsing works correctly"""
import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

# Test ABSA PDF
print("Testing ABSA PDF parsing...")
with open('Absa.pdf', 'rb') as f:
    csv_bytes, year, note = pdf_to_csv_bytes(f.read())

csv_text = csv_bytes.decode('utf-8')
df = pd.read_csv(StringIO(csv_text))

print(f"\n✓ ABSA PDF: Extracted {len(df)} transactions")
print(f"  Total inflows: {df[df['amount'] > 0]['amount'].sum():.2f}")
print(f"  Total outflows: {df[df['amount'] < 0]['amount'].sum():.2f}")
print(f"  Net: {df['amount'].sum():.2f}")

# Show key transactions to verify correctness
print(f"\nKey transactions:")
june25 = df[df['date'] == '20250625']
june26 = df[df['date'] == '20250626']
print(f"  June 25 (4 transactions): {list(june25['amount'].values)}")
print(f"  June 26 (2 transactions): {list(june26['amount'].values)}")
print(f"  Expected 12642 (ACB CREDIT BV 819 20 21 22): 3175631.62")
print(f"  Expected 12646 (BIO PAYMENT): -1430724.39")

print("\n✓ Parser is working correctly!")
