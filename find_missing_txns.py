#!/usr/bin/env python3
"""
Find which transaction rows from the PDF are NOT being parsed
"""
import sys
sys.path.insert(0, 'backend')

import pdfplumber
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

pdf_path = "Capitec.pdf"

# Get all transaction rows from PDF
pdf_transactions = []
with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            if table and len(table) == 1:
                row = table[0]
                if len(row) >= 7:
                    date_str = str(row[0]).strip() if row[0] else ""
                    # Check if this looks like a transaction (has date, description, and amount columns)
                    if len(date_str) > 0 and any(c.isdigit() for c in date_str):
                        # Check if it has any amount values
                        has_amount = False
                        for col_idx in [3, 5, 7]:  # Money In, Money Out, Fee columns
                            if col_idx < len(row) and row[col_idx]:
                                cell_str = str(row[col_idx]).strip()
                                if cell_str and any(c.isdigit() for c in cell_str):
                                    has_amount = True
                                    break
                        
                        # Also accept if it's a header row
                        is_header = 'date' in str(row[0]).lower() and 'description' in str(row[1]).lower() if len(row) > 1 else False
                        
                        if has_amount or is_header:
                            desc = str(row[1]).strip() if len(row) > 1 else ""
                            pdf_transactions.append({
                                'date': date_str,
                                'description': desc,
                                'page': page_num + 1,
                                'table': table_idx + 1,
                                'row': row
                            })

print(f"Total potential transaction rows in PDF: {len(pdf_transactions)}")

# Get parsed transactions
with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

csv_bytes, _ = pdf_to_csv_bytes(pdf_content)
df = pd.read_csv(io.BytesIO(csv_bytes))

print(f"Total parsed transactions: {len(df)}\n")

# Find what's missing
parsed_dates = set(df['date'].unique())
pdf_dates = set(t['date'] for t in pdf_transactions if t['date'])

print(f"Dates in PDF: {sorted(pdf_dates)}\n")
print(f"Dates parsed: {sorted(parsed_dates)}\n")

# Find missing rows - rows that are in PDF but not in parsed data
missing = []
for txn in pdf_transactions:
    if txn['date'] not in parsed_dates:
        missing.append(txn)

if missing:
    print(f"❌ Found {len(missing)} rows in PDF that weren't parsed:\n")
    for txn in missing[:10]:  # Show first 10
        print(f"  {txn['date']} | {txn['description'][:50]}")
        print(f"    Page {txn['page']}, Table {txn['table']}")
        print(f"    Row: {[str(c)[:20] if c else '' for c in txn['row'][:9]]}")
        print()
else:
    print("✓ All PDF rows were parsed")

# Also check if some dates exist but with fewer transactions than in PDF
print("\n--- Transaction count by date ---")
from collections import defaultdict
pdf_by_date = defaultdict(int)
parsed_by_date = defaultdict(int)

for txn in pdf_transactions:
    if txn['date']:
        pdf_by_date[txn['date']] += 1

for date in df['date'].unique():
    parsed_by_date[date] += len(df[df['date'] == date])

all_dates = sorted(set(list(pdf_by_date.keys()) + list(parsed_by_date.keys())))
mismatches = []
for date in all_dates:
    pdf_count = pdf_by_date.get(date, 0)
    parsed_count = parsed_by_date.get(date, 0)
    if pdf_count != parsed_count:
        mismatches.append((date, pdf_count, parsed_count))
        print(f"  {date}: PDF has {pdf_count}, Parsed has {parsed_count}")

if not mismatches:
    print("✓ All dates have matching transaction counts")
