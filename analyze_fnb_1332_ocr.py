#!/usr/bin/env python
"""Analyze the FNB OCR text format to build a parser"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pdf2image import convert_from_bytes
import pytesseract

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

images = convert_from_bytes(pdf_content, dpi=200)
img = images[0].convert('L')
ocr_text = pytesseract.image_to_string(img, lang='eng')

print("="*80)
print("FULL OCR TEXT")
print("="*80)
print(ocr_text)
print("="*80)

# Analyze line by line
print("\n\nLINE-BY-LINE ANALYSIS")
print("="*80)
for i, line in enumerate(ocr_text.split('\n'), 1):
    if line.strip():
        print(f"{i:3d}: {line}")
