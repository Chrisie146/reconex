"""Check if 635027 transaction is in CSV."""
import csv

with open('debug_out_standard_bank_fresh.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        amt_str = row['amount']
        try:
            amt = float(amt_str)
            if abs(amt) > 630000:
                print(f"{row['date']} | {row['description'][:50]:50} | {amt}")
        except:
            pass
