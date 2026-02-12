#!/usr/bin/env python
"""Inspect the raw FNB_ASPIRE_CURRENT_ACCOUNT_132.PDF structure"""
import pdfplumber

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_132.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    # Check first page
    page = pdf.pages[0]
    print(f"\n=== PAGE 1 TEXT (first 2000 chars) ===")
    text = page.extract_text()
    print(text[:2000])
    
    print(f"\n=== PAGE 1 TABLES ===")
    tables = page.extract_tables()
    print(f"Number of tables: {len(tables)}")
    
    if tables:
        for i, table in enumerate(tables):
            print(f"\nTable {i+1}:")
            print(f"  Rows: {len(table)}")
            print(f"  Columns: {len(table[0]) if table else 0}")
            
            # Show header
            if table and len(table) >= 1:
                print(f"\n  Header:")
                print(f"    {table[0]}")
                
                # Show first 10 data rows
                if len(table) > 1:
                    print(f"\n  First 10 data rows:")
                    for j, row in enumerate(table[1:11]):
                        print(f"    Row {j+1}: {row}")
    
    # Try to extract text lines to understand the transaction structure
    print(f"\n\n=== TRANSACTION TEXT LINES (lines 15-60) ===")
    lines = text.split('\n')
    for i, line in enumerate(lines[15:60], 15):
        print(f"{i:3d}: {line}")
