#!/usr/bin/env python
"""Check entry 12659 extraction"""
import sys
sys.path.insert(0, 'backend')

from pdf2image import convert_from_path
import pytesseract
import re

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

print("Lines with 12659, 12660, etc:")
for i, line in enumerate(lines):
    if any(s in line for s in ['12658', '12659', '12660', '12661']):
        print(f"Line {i}: {line!r}")
        
        # Check if this line matches the extraction criteria
        line_strip = line.strip()
        if line_strip and line_strip[0].isdigit():
            entry_match = re.match(r'^(\d{2,5})\s', line_strip)
            date_match = re.search(r'\b(\d{6})\b', line_strip) if entry_match else None
            
            if entry_match:
                print(f"  ✓ Entry match: {entry_match.group(1)}")
            if date_match:
                print(f"  ✓ Date match: {date_match.group(1)}")
            elif entry_match:
                print(f"  ✗ NO DATE MATCH!")
        print()
