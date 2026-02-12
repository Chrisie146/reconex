"""Extract OCR text from the PDF and save it."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from services.ocr import ocr_pdf_bytes

pdf_path = 'xxxxx0819_31.12.25.pdf'

# Read PDF bytes
with open(pdf_path, 'rb') as f:
    file_bytes = f.read()

print(f"Extracting OCR from {pdf_path}...")
ocr_text = ocr_pdf_bytes(file_bytes)

# Save to file for inspection
with open('ocr_output_sb_full.txt', 'w') as f:
    f.write(ocr_text)

print(f"✓ Saved OCR text to ocr_output_sb_full.txt")
print(f"✓ OCR text length: {len(ocr_text)} characters")

# Show lines with the large amounts
lines = ocr_text.split('\n')
search_amounts = ['372423', '240157', '635027', '332925']

print()
print("LINES WITH LARGE AMOUNTS:")
for i, line in enumerate(lines):
    for amount in search_amounts:
        if amount in line:
            # Show context
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            print(f"\nFound '{amount}' at line {i}:")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"{marker} {lines[j]}")

# Scan for large amounts using regex
import re

print("\nTOP LARGE AMOUNTS FOUND IN OCR:")
amount_matches = []
for i, line in enumerate(lines):
    for match in re.finditer(r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b", line):
        raw = match.group(0)
        try:
            val = float(raw.replace(',', ''))
            if val >= 100000:
                amount_matches.append((val, i, line.strip()))
        except ValueError:
            pass

amount_matches.sort(reverse=True, key=lambda x: x[0])
for val, i, line in amount_matches[:20]:
    print(f"  {val:,.2f} | line {i} | {line[:120]}")
