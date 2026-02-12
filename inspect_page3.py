#!/usr/bin/env python
"""Inspect page 3 structure in detail"""
import sys, os
sys.path.insert(0, 'backend')

from pdf2image import convert_from_path
import pytesseract

pdf_path = '20260119115115880.pdf'
images = convert_from_path(pdf_path, dpi=300)

# Get page 3 OCR (index 2)
text = pytesseract.image_to_string(images[2])

# Show full page
lines = text.split('\n')
print(f"Page 3 has {len(lines)} lines\n")
print("Full Page 3 OCR Text:")
print("=" * 100)
print(text[:2000])  # First 2000 chars
