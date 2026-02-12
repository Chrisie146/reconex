#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from services.pdf_parser import pdf_to_csv_bytes
from services.parser import validate_csv, normalize_csv
import pandas as pd

content = open('Standard bank.pdf','rb').read()
csv_bytes, statement_year, detected_bank = pdf_to_csv_bytes(content)

# Convert to DataFrame for easier analysis
csv_str = csv_bytes.decode('utf-8')
lines = csv_str.strip().split('\n')

rows = []
for line in lines[1:]:  # Skip header
    parts = line.split(',')
    if len(parts) >= 3:
        rows.append({
            'date': parts[0],
            'description': parts[1],
            'amount': float(parts[2])
        })

df = pd.DataFrame(rows)
print(f"Total transactions: {len(df)}")
print(f"Current NET: R {df['amount'].sum():,.2f}")
print(f"Target NET: R 988,465.27\n")

# Check for exact duplicates
dupes = df[df.duplicated(subset=['date', 'description', 'amount'], keep=False)].sort_values(['date', 'description', 'amount'])
print(f"Rows with duplicate date+description+amount: {len(dupes)}")

if len(dupes) > 0:
    dupe_groups = dupes.groupby(['date', 'description', 'amount'])
    print(f"Unique duplicate groups: {len(dupe_groups)}\n")
    
    print("Duplicate groups (first 15):")
    for i, ((date, desc, amt), group) in enumerate(list(dupe_groups)[:15]):
        print(f"  {i+1}. {date} | {desc[:60]} | R {amt:,.2f} | Count: {len(group)}")
    
    # Calculate impact of removing duplicates
    duplicate_amount = 0
    for (date, desc, amt), group in dupe_groups:
        if len(group) > 1:
            # Keep first, remove rest
            duplicate_amount += amt * (len(group) - 1)
    
    print(f"\nTotal amount in duplicates (to remove): R {duplicate_amount:,.2f}")
    print(f"Net after removing duplicates: R {df['amount'].sum() - duplicate_amount:,.2f}")
