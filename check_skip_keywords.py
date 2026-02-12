#!/usr/bin/env python
"""Check entry 12659 against skip keywords"""
import sys
sys.path.insert(0, 'backend')

from pdf2image import convert_from_path
import pytesseract

# Get OCR text
images = convert_from_path('Absa.pdf', dpi=200)
ocr_texts = []
for idx, img in enumerate(images, start=1):
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    if text:
        ocr_texts.append(text)

all_text = '\n'.join(ocr_texts)
lines = all_text.split('\n')

skip_keywords = [
    "Entry", "No", "Date", "Description",
    "Start Date", "End Date",
    "Statement Enquiry", "Account", "Branch",
    "Balance", "Amount", "Site",
    "Page", "Reg no",
    "Regional", "Service Centre",
    "Wed,", "at", "BIO CASE"
]

target_line = "12659 250628 POS PURCHASE (EFFEC 27062025) Yoco *Leather"

print(f"Target line: {target_line!r}")
print()
print("Skip keyword check:")
for kw in skip_keywords:
    if kw in target_line:
        print(f"  ✓ CONTAINS '{kw}'")

if not any(kw in target_line for kw in skip_keywords):
    print("  ✓ NO SKIP KEYWORDS FOUND - should be extracted!")
