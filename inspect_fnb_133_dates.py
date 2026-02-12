"""Inspect FNB_ASPIRE_CURRENT_ACCOUNT_133.pdf for year detection issue"""

import io
import re
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

try:
    from pdf2image import convert_from_bytes
    import pytesseract
except Exception as e:
    print(f"Error importing OCR dependencies: {e}")
    sys.exit(1)

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_133.pdf'

print(f"Extracting text from: {pdf_path}")
print("=" * 80)

# Read the PDF
with open(pdf_path, 'rb') as f:
    file_content = f.read()

# Convert to images and OCR
images = convert_from_bytes(file_content, dpi=200)
ocr_texts = []

for idx, img in enumerate(images, start=1):
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    if text:
        ocr_texts.append(text)
        print(f"\n{'='*80}")
        print(f"PAGE {idx}")
        print('='*80)
        print(text[:1500])  # Print first 1500 chars of each page

# Analyze year occurrences
full_ocr_text = '\n'.join(ocr_texts)
year_matches = re.findall(r'\b(20[0-2][0-9])\b', full_ocr_text)

print(f"\n{'='*80}")
print("YEAR ANALYSIS")
print('='*80)
print(f"All years found: {year_matches}")

from collections import Counter
if year_matches:
    cnt = Counter(year_matches)
    print(f"\nYear counts: {cnt}")
    most_common_year = int(cnt.most_common(1)[0][0])
    print(f"Most common year: {most_common_year}")

# Look for statement period
print(f"\n{'='*80}")
print("LOOKING FOR STATEMENT PERIOD")
print('='*80)
statement_period_match = re.search(r'Statement Period[:\s]+.*?(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+to\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', full_ocr_text, re.IGNORECASE)
if statement_period_match:
    print(f"Found: {statement_period_match.group(0)}")
    print(f"  From: {statement_period_match.group(1)} {statement_period_match.group(2)} {statement_period_match.group(3)}")
    print(f"  To: {statement_period_match.group(4)} {statement_period_match.group(5)} {statement_period_match.group(6)}")
else:
    # Try simpler pattern
    print("Trying simpler pattern...")
    date_patterns = re.findall(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', full_ocr_text, re.IGNORECASE)
    print(f"Found {len(date_patterns)} date patterns:")
    for pattern in date_patterns[:10]:
        print(f"  {pattern[0]} {pattern[1]} {pattern[2]}")

# Look for specific months like December
print(f"\n{'='*80}")
print("DECEMBER OCCURRENCES")
print('='*80)
december_matches = re.findall(r'(\d{1,2})\s+Dec(?:ember)?\s+(\d{4})', full_ocr_text, re.IGNORECASE)
print(f"December dates found: {december_matches}")
