#!/usr/bin/env python
"""Check how many pages are in the FNB PDF"""
import pdfplumber

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    for page_num, page in enumerate(pdf.pages, 1):
        text = page.extract_text()
        lines = text.split('\n') if text else []
        print(f"\nPage {page_num}:")
        print(f"  Text length: {len(text) if text else 0} chars")
        print(f"  Lines: {len(lines)}")
        if lines:
            print(f"  First line: {lines[0][:50] if lines[0] else 'empty'}")
            print(f"  Last line: {lines[-1][:50] if lines[-1] else 'empty'}")
