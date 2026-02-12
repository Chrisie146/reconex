#!/usr/bin/env python
"""Find why entry 12659 is missing"""
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

# Search for 12659
if '12659' in all_text:
    idx = all_text.find('12659')
    print("Found 12659 at position", idx)
    print("\nContext around 12659:")
    print(all_text[max(0, idx-100):idx+200])
else:
    print("12659 NOT found in OCR text!")
    
# Look for entries between 12658 and 12660
for entry in [12657, 12658, 12659, 12660, 12661]:
    if str(entry) in all_text:
        print(f"✓ Entry {entry} found")
    else:
        print(f"✗ Entry {entry} NOT found")
