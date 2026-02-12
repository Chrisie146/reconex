#!/usr/bin/env python3
import pdfplumber

with pdfplumber.open('Capitec.pdf') as pdf:
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            if table and len(table) == 1:
                row = table[0]
                if row and len(row) > 0:
                    date_str = str(row[0]).strip() if row[0] else ''
                    if date_str == '11/01/2026':
                        print(f'11/01/2026 row (Page {page_num+1}, Table {table_idx+1}):')
                        print(f'  Columns: {len(row)}')
                        for i, cell in enumerate(row):
                            print(f'  [{i}] {repr(cell)}')
