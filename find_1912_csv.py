#!/usr/bin/env python3
"""
Search for the 19/12 SMS row in CSV
"""
import sys
sys.path.insert(0, 'backend')

from backend.services.pdf_parser import pdf_to_csv_bytes

pdf_path = "Capitec.pdf"

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, _ = pdf_to_csv_bytes(pdf_content)

lines = csv_bytes.decode('utf-8').split('\n')
for i, line in enumerate(lines):
    if '19/12' in line and 'SMS' in line:
        print(f"Row {i}: {line[:150]}")
        # Show context
        print(f"Row {i-1}: {lines[i-1][:150] if i > 0 else ''}")
        print(f"Row {i+1}: {lines[i+1][:150] if i+1 < len(lines) else ''}")
