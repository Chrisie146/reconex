"""Check for SCHOLAR and GET AHEAD transactions."""
import csv

with open('debug_out_standard_bank_fresh.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        desc = row['description'].upper()
        if 'SCHOLAR' in desc or 'GETAHEAD' in desc or 'GET AHEAD' in desc:
            print(f"{row['date']} | {row['description'][:70]:70} | {row['amount']}")
