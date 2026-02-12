#!/usr/bin/env python3
"""
Show ALL tables on page 4 around 19/12
"""
import pdfplumber

pdf_path = "Capitec.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[3]  # Page 4
    tables = page.extract_tables()
    
    print(f"Page 4 has {len(tables)} tables\n")
    
    for table_idx in range(25, min(31, len(tables))):
        table = tables[table_idx]
        print(f"=== Table {table_idx+1} ===")
        print(f"Dimensions: {len(table)} rows x {len(table[0]) if table else 0} cols")
        
        if table and len(table) > 0:
            # Show first row
            print(f"First row (col 0): {repr(str(table[0][0])[:30] if table[0] else '')}")
            
            # Show all rows with data
            for row_idx, row in enumerate(table):
                if row:
                    # Check if this row has 19/12
                    if "19/12" in str(row[0]):
                        print(f"  Row {row_idx} (19/12):")
                        for col_idx in [0, 1, 2, 5, 7, 8]:
                            if col_idx < len(row):
                                print(f"    [{col_idx}] {repr(str(row[col_idx])[:40])}")
        print()
