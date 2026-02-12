#!/usr/bin/env python3
"""
Dump the raw CSV to see what's being generated
"""
import sys
sys.path.insert(0, 'backend')

from backend.services.pdf_parser import pdf_to_csv_bytes
import io

pdf_path = "Capitec.pdf"

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, _ = pdf_to_csv_bytes(pdf_content)

# Show raw CSV around row 65
lines = csv_bytes.decode('utf-8').split('\n')
print("CSV rows 60-70:")
for i in range(60, min(70, len(lines))):
    print(f"{i}: {lines[i][:150]}")
