#!/usr/bin/env python
"""Inspect raw OCR output from FNB PDF 20260119115115880"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io

pdf_path = '20260119115115880.pdf'

print("="*80)
print("Inspecting OCR Output: 20260119115115880.pdf")
print("="*80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"\nTotal pages: {len(pdf.pages)}")
    
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n{'='*80}")
        print(f"PAGE {page_num}")
        print('='*80)
        
        # Check if it's a scanned page (text extraction will be empty/minimal)
        try:
            text = page.extract_text()
            if text and len(text.strip()) > 100:
                print("[✓] Has extractable text (likely digital PDF)")
                print("\nExtracted text sample:")
                print(text[:500])
            else:
                print("[!] Minimal extractable text (likely scanned/image PDF)")
        except:
            print("[!] Could not extract text (scanned PDF)")
        
        # Try to perform OCR on this page
        try:
            # Convert page to image and perform OCR
            images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
            if images:
                img = images[0]
                ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text and len(ocr_text.strip()) > 0:
                    print(f"\n[OCR Text (first 800 chars)]:")
                    print("-" * 80)
                    lines = ocr_text.split('\n')
                    for i, line in enumerate(lines[:30], 1):
                        if line.strip():
                            print(f"{i:3d}: {repr(line)}")
                    print(f"\n... ({len(lines)} total lines on page)")
                else:
                    print("[!] OCR produced no text")
        except Exception as e:
            print(f"[!] OCR failed: {e}")
