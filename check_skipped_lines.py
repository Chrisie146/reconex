"""Check which OCR lines are being skipped by the parser."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path('.') / 'backend'))
from services.pdf_parser import convert_from_bytes, pytesseract
import re

pdf_path = 'xxxxx0819_31.12.25.pdf'
with open(pdf_path, 'rb') as f:
    file_content = f.read()

images = convert_from_bytes(file_content, dpi=200)
ocr_texts = []
for img in images:
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    ocr_texts.append(text)

full_ocr = '\n'.join(ocr_texts)
lines = full_ocr.split('\n')

skip_keywords = [
    "CURRENT ACCOUNT",
    "DETAILS SERVICE",
    "STANDARD BANK",
    "STATEMENT",
    "BALANCE BROUGHT FORWARD",
    "BALANCE CARRIED",
    "BALANCE BROUGHT",
    "THE HEADMASTER",
    "GET AHEAD",
    "PAGE ",
    "STNDRDBANK",
    "BASC"
]

skipped_lines = []
for line in lines:
    line_upper = line.upper()
    if line and any(k in line_upper for k in skip_keywords):
        # Check if this looks like a transaction that shouldn't be skipped
        if any(x in line for x in ['TRANSFER', 'CREDIT', 'DEBIT', 'PAYMENT', 'DEPOSIT']):
            # Has transaction keywords but also has skip keywords
            skipped_lines.append((line, [k for k in skip_keywords if k in line_upper]))

print(f"Lines with both transaction keywords AND skip keywords: {len(skipped_lines)}")
for line, keywords in skipped_lines:
    print(f"  Skipped keywords: {keywords}")
    print(f"  Line: {line[:80]}")
    print()
