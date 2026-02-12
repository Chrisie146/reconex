#!/usr/bin/env python3
"""
Show full table 28 (2-row table with 19/12)
"""
import pdfplumber

pdf_path = "Capitec.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[3]  # Page 4
    tables = page.extract_tables()
    
    table = tables[27]  # Table 28 (0-indexed)
    
    print(f"Table 28: {len(table)} rows x {len(table[0]) if table else 0} cols\n")
    
    for row_idx, row in enumerate(table):
        print(f"Row {row_idx}:")
        for col_idx, cell in enumerate(row):
            if cell:
                print(f"  [{col_idx}] {repr(str(cell)[:60])}")
            else:
                print(f"  [{col_idx}] (empty)")
        print()
