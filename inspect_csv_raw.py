"""Inspect the actual CSV bytes returned by pdf_to_csv_bytes"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_133.pdf'

print(f"Parsing: {pdf_path}")
print("=" * 80)

# Read and parse the PDF
with open(pdf_path, 'rb') as f:
    file_content = f.read()

csv_bytes, statement_year, bank = pdf_to_csv_bytes(file_content)

# Convert to string and show first 2000 chars
csv_text = csv_bytes.decode('utf-8')

print("CSV OUTPUT (first 3000 chars):")
print("=" * 80)
print(csv_text[:3000])

print("\n" + "=" * 80)
print("SEARCHING FOR DECEMBER DATES WITH YEAR:")
print("=" * 80)
lines = csv_text.split('\n')
for i, line in enumerate(lines):
    if 'Dec' in line or '12' in line:
        if i < 20:  # Only show early lines
            print(f"Line {i}: {line}")
        if '2025' in line:
            print(f"Line {i} HAS 2025: {line}")
        if '2026' in line:
            print(f"Line {i} HAS 2026: {line}")

print("\n" + "=" * 80)
print("SEARCHING FOR JANUARY DATES WITH YEAR:")
print("=" * 80)
for i, line in enumerate(lines):
    if 'Jan' in line or '/01/' in line or '-01-' in line:
        if i < 150 and i > 100:  # Show lines around January start
            print(f"Line {i}: {line[:80]}")
