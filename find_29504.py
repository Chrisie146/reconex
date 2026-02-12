"""Find transactions around 29504 amount."""
import csv

with open('debug_out_standard_bank_fresh.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            amt = float(row['amount'])
            # Check amounts close to the 29504 delta
            if 29000 < abs(amt) < 30000:
                print(f"{row['date']} | {row['description'][:40]:40} | {amt:12.2f}")
        except:
            pass
