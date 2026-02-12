#!/usr/bin/env python3
import pdfplumber

with pdfplumber.open('Capitec.pdf') as pdf:
    # Check last page for 11/01
    page = pdf.pages[-1]
    tables = page.extract_tables()
    print(f"Last page has {len(tables)} tables\n")
    
    for table_idx, table in enumerate(tables[-5:]):  # Last 5 tables
        if table:
            print(f"Table {len(tables)-5+table_idx}:")
            print(f"  Rows: {len(table)}, Cols: {len(table[0]) if table else 0}")
            if table and len(table) <= 3:
                for row_idx, row in enumerate(table):
                    cells = [str(c)[:20] if c else '' for c in row[:9]]
                    print(f"    Row {row_idx}: {cells}")
            print()
