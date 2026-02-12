"""Check the context around large amounts in the PDF."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from services.pdf_parser import extract_text_from_pdf

pdf_path = 'xxxxx0819_31.12.25.pdf'

# Extract text from all pages
text = extract_text_from_pdf(pdf_path)
lines = text.split('\n')

# Find lines with R372,423.59, R240,157, R635,027.18, or R332,925.71
search_amounts = ['372423', '240157', '635027', '332925', '372,423', '240,157', '635,027', '332,925']

print("SEARCHING FOR LARGE AMOUNTS IN PDF...")
print()

for i, line in enumerate(lines):
    for amount in search_amounts:
        if amount in line:
            # Show context: this line and 2 before/after
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            print(f"Found '{amount}' at line {i}:")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"{marker} {lines[j]}")
            print()
