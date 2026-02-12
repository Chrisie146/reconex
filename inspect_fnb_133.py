"""Inspect FNB_ASPIRE_CURRENT_ACCOUNT_133.pdf for date parsing issue"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from pdf_extractor import extract_text_from_pdf
from fnb_parser import parse_fnb_statement

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_133.pdf'

print(f"Extracting text from: {pdf_path}")
print("=" * 80)

text = extract_text_from_pdf(pdf_path)
print("RAW OCR OUTPUT (first 3000 chars):")
print(text[:3000])
print("\n" + "=" * 80)

# Show first few lines with dates
print("\nSearching for date patterns in OCR:")
lines = text.split('\n')
for i, line in enumerate(lines[:100]):
    if any(c.isdigit() for c in line):
        print(f"Line {i}: {line}")

print("\n" + "=" * 80)
print("\nParsing statement...")

# Try parsing with 2025
result = parse_fnb_statement(text, 2025)
print(f"\nParsed {len(result['transactions'])} transactions with year=2025")
if result['transactions']:
    print("\nFirst 5 transactions:")
    for txn in result['transactions'][:5]:
        print(f"  {txn}")
    print("\nLast 5 transactions:")
    for txn in result['transactions'][-5:]:
        print(f"  {txn}")

# Try parsing with 2026
print("\n" + "=" * 80)
result = parse_fnb_statement(text, 2026)
print(f"\nParsed {len(result['transactions'])} transactions with year=2026")
if result['transactions']:
    print("\nFirst 5 transactions:")
    for txn in result['transactions'][:5]:
        print(f"  {txn}")
    print("\nLast 5 transactions:")
    for txn in result['transactions'][-5:]:
        print(f"  {txn}")
