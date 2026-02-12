#!/usr/bin/env python3
"""
Check what's on 19/12 and 24/11 in the PDF - should be only 1 row each
"""
import pdfplumber

with pdfplumber.open('Capitec.pdf') as pdf:
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table in tables:
            if table and len(table) >= 1:
                row = table[0]
                if len(row) > 0:
                    date_str = str(row[0]).strip() if row[0] else ''
                    if date_str in ['19/12/2025', '24/11/2025']:
                        print(f'{date_str} - Table with {len(table)} rows, {len(row)} columns:')
                        for row_idx, r in enumerate(table):
                            cells = [str(c)[:20] if c else '' for c in r[:9]]
                            print(f'  Row {row_idx}: {cells}')
                        print()
