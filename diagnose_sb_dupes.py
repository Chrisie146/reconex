#!/usr/bin/env python3
import pandas as pd

# Load CSV
df = pd.read_csv('parsed_transactions.csv')

# Filter to Standard Bank only
sb = df[df['Bank'] == 'Standard Bank'].copy()
print(f"Total Standard Bank transactions: {len(sb)}")
print(f"Unique dates: {sb['Date'].nunique()}\n")

# Calculate sum
total = sb['Amount'].sum()
print(f"Current NET (with duplicates): R {total:,.2f}")
print(f"Target NET: R 988,465.27\n")

# Find exact duplicates
dupes = sb[sb.duplicated(subset=['Date', 'Description', 'Amount'], keep=False)].sort_values(['Date', 'Description', 'Amount'])
print(f"Exact duplicates (date+desc+amount): {len(dupes)}")
if len(dupes) > 0:
    dupe_groups = dupes.groupby(['Date', 'Description', 'Amount'])
    print(f"Duplicate transaction groups: {len(dupe_groups)}\n")
    
    print("Duplicate groups (showing first 10):")
    for i, ((date, desc, amt), group) in enumerate(list(dupe_groups)[:10]):
        print(f"  {i+1}. {date} | {desc[:50]} | R {amt:,.2f} | Count: {len(group)}")
