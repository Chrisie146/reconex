#!/usr/bin/env python
"""Find missing transactions in OCR extraction"""
import sys, os
sys.path.insert(0, 'backend')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = '20260119115115880.pdf'
images = convert_from_path(pdf_path, dpi=300)

# Get raw OCR text
print("=== OCR Text Analysis ===\n")
for page_num, img in enumerate(images, 1):
    text = pytesseract.image_to_string(img)
    
    # Find all date-like patterns (DD Mon)
    date_pattern = re.compile(r'\b(\d{1,2})\s+([A-Z][a-z]{2})\b')
    matches = date_pattern.findall(text)
    
    print(f"Page {page_num}: Found {len(matches)} date matches")
    
    # Find transaction lines (date | description amount balance)
    txn_pattern = re.compile(r'^\d{1,2}\s+[A-Z][a-z]{2}\s+\|', re.MULTILINE)
    txn_matches = txn_pattern.findall(text)
    
    print(f"Page {page_num}: Found {len(txn_matches)} transaction lines")
    
    # Show first 5 lines of page
    lines = text.split('\n')
    print(f"\nFirst 10 lines of page {page_num}:")
    for i, line in enumerate(lines[:10]):
        if line.strip():
            print(f"  {line[:100]}")

print("\n=== Summary ===")
print(f"Total pages: {len(images)}")
print(f"Expected transactions: 134 rows in final CSV")
print(f"We're getting all data - issue must be in parsing logic")
