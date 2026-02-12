#!/usr/bin/env python
"""Check amounts for entries 12659-12667"""
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

# Extract amounts from both sections and track which section they come from
amounts = []
search_pos = 0
section_num = 0

while True:
    amount_idx = all_text.find('Amount', search_pos)
    if amount_idx < 0:
        break
    
    section_num += 1
    balance_idx = all_text.find('Balance', amount_idx)
    if balance_idx < 0:
        balance_idx = len(all_text)
    
    amount_section = all_text[amount_idx:balance_idx]
    
    amount_pattern = re.compile(r'-?\d+\s*\.\d{2}')
    for match in amount_pattern.finditer(amount_section):
        try:
            amount_text = match.group(0).replace(' ', '')
            amount = float(amount_text)
            amounts.append((amount, section_num))
        except ValueError:
            pass
    
    search_pos = balance_idx

print(f"Total amounts: {len(amounts)}")
print()
print("Last 15 amounts (from both sections):")
for i in range(max(0, len(amounts)-15), len(amounts)):
    amount, section = amounts[i]
    section_label = f"Section {section}"
    print(f"  {i:<3}: {amount:>15.2f} ({section_label})")
