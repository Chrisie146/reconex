"""Dump rows before CSV conversion to inspect the 9484 entry."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from services.pdf_parser import pdf_to_csv_bytes, _parse_standard_bank_business_text

pdf_path = 'xxxxx0819_31.12.25.pdf'
with open(pdf_path, 'rb') as f:
    file_content = f.read()

# Run OCR parsing path manually
from services.pdf_parser import convert_from_bytes, pytesseract

# Convert pages like pdf_to_csv_bytes
images = convert_from_bytes(file_content, dpi=200)
ocr_texts = []
for img in images:
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    ocr_texts.append(text)

full_ocr = '\n'.join(ocr_texts)

# Parse using the business parser
rows = _parse_standard_bank_business_text(full_ocr, pdf=None, statement_year=2025)

print(f"Parsed rows count: {len(rows)}")
for i, r in enumerate(rows[:60]):
    print(i+1, r)
    if '9484' in r[1] or '9484' in r[2]:
        print("--> FOUND 9484 in parsed rows above")

# Also run pdf_to_csv_bytes to show CSV converted rows
csv_bytes, _, _ = pdf_to_csv_bytes(file_content)
print('\nCSV preview (first 40 lines):')
print(csv_bytes.decode('utf-8').split('\n')[:40])
