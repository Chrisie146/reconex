"""Check what statement year is being extracted from the OCR."""

import re

with open('ocr_output_sb_full.txt', 'r') as f:
    ocr_text = f.read()

year_match = re.search(r'Statement from.*?(\d{4})', ocr_text, re.IGNORECASE)
if year_match:
    print(f"Found year: {year_match.group(1)}")
    print(f"Full match: {year_match.group(0)}")
else:
    print("No year found")

# Also check for other patterns
for line in ocr_text.split('\n'):
    if 'Statement' in line and 'from' in line.lower():
        print(f"Statement line: {line}")
