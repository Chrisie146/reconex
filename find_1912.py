#!/usr/bin/env python3
import pdfplumber

with pdfplumber.open('Capitec.pdf') as pdf:
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table in tables:
            if table and len(table) == 1:
                row = table[0]
                if row and len(row) > 0:
                    date_str = str(row[0]).strip() if row[0] else ''
                    if date_str == '19/12/2025':
                        print(f'19/12/2025 row found:')
                        for i, cell in enumerate(row):
                            print(f'  [{i}] {repr(cell)}')
