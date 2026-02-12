#!/usr/bin/env python
"""Check the raw CSV output from FNB parser"""
import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_132.pdf'
with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, year, detected_bank = pdf_to_csv_bytes(pdf_content)
print(f"Detected bank: {detected_bank}")
print(f"Statement year: {year}")

# Show first 50 lines of CSV
csv_text = csv_bytes.decode('utf-8')
lines = csv_text.split('\n')
print(f"\nTotal lines: {len(lines)}")
print("\nFirst 30 lines:")
for i, line in enumerate(lines[:30]):
    print(f"{i:3d}: {line}")

print("\n\n=== Lines 50-80 ===")
for i, line in enumerate(lines[50:80], 50):
    print(f"{i:3d}: {line}")

# Check for problematic amounts
print("\n\n=== Checking amounts ===")
for i, line in enumerate(lines[1:]):  # Skip header
    parts = line.split(',')
    if len(parts) >= 3:
        amount = parts[2].strip()
        if 'C' in amount or 'r' in amount:
            print(f"Line {i+1}: {line[:80]}... (has C/r suffix)")
            if i > 10:  # Just show first few
                break
