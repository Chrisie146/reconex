#!/usr/bin/env python3
"""
Find all SMS fee transactions and check their amounts in PDF
"""
import sys
sys.path.insert(0, 'backend')

import pdfplumber

pdf_path = "Capitec.pdf"

print("Scanning all SMS notification fee rows...\n")

# Look for all SMS fee rows
sms_count = 0
with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            if table and len(table) == 1:
                row = table[0]
                if row and len(row) > 1:
                    desc_cell = str(row[1] if len(row) > 1 else "")
                    if "SMS" in desc_cell and "Notification" in desc_cell:
                        sms_count += 1
                        date_cell = str(row[0]).strip() if row[0] else ""
                        print(f"SMS Fee #{sms_count} - Date: {date_cell}")
                        print(f"  Columns ({len(row)}):")
                        for col_idx, cell in enumerate(row):
                            if cell:
                                print(f"    [{col_idx}] {repr(cell)}")
                        print()
                        if sms_count >= 10:
                            break
        if sms_count >= 10:
            break
