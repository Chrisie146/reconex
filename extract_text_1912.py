#!/usr/bin/env python3
"""
Extract raw text around 19/12 to see if transfer is mentioned
"""
import pdfplumber

pdf_path = "Capitec.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[3]  # Page 4
    text = page.extract_text()
    
    # Find lines with 19/12
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if '19/12' in line:
            print(f"Line {i}: {line}")
            # Show next few lines too
            for j in range(1, 4):
                if i+j < len(lines):
                    print(f"Line {i+j}: {lines[i+j]}")
            print()
