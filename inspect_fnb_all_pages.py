#!/usr/bin/env python
"""Check all pages of FNB_ASPIRE_CURRENT_ACCOUNT_132.PDF"""
import pdfplumber

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_132.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")
    
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"=== PAGE {page_num} ===")
        
        # Extract tables
        tables = page.extract_tables()
        print(f"  Tables: {len(tables)}")
        
        for i, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
                
            # Check if this looks like a transaction table
            header = table[0] if table else []
            header_str = ' '.join([str(h) for h in header if h])
            
            if 'Date' in header_str or 'Description' in header_str or 'Amount' in header_str:
                print(f"\n  Transaction Table {i+1}:")
                print(f"    Rows: {len(table)}")
                print(f"    Columns: {len(table[0]) if table else 0}")
                print(f"    Header: {header}")
                
                # Count amounts in merged cell (row 1, column 2)
                if len(table) > 1 and len(table[1]) > 2:
                    amounts_cell = table[1][2]
                    if amounts_cell:
                        amounts_list = [a.strip() for a in str(amounts_cell).split('\n') if a.strip()]
                        print(f"    Amounts in merged cell: {len(amounts_list)}")
                        print(f"    First 5 amounts: {amounts_list[:5]}")
                        print(f"    Last 5 amounts: {amounts_list[-5:]}")
                
                # Count date rows (rows with date in column 0)
                date_count = 0
                for row in table[2:]:
                    if row and row[0] and str(row[0]).strip():
                        date_count += 1
                print(f"    Date rows: {date_count}")
        
        print()
