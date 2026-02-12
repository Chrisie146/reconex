"""Check what's being extracted for CREDIT TRANSFER 9484 from the actual PDF."""

import sys
import csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = 'xxxxx0819_31.12.25.pdf'

with open(pdf_path, 'rb') as f:
    file_content = f.read()

csv_bytes, _, _ = pdf_to_csv_bytes(file_content)

# Parse CSV and find CREDIT TRANSFER 9484
csv_text = csv_bytes.decode('utf-8')
lines = csv_text.split('\n')

print("Searching for 'CREDIT TRANSFER 9484' or 'CREDIT TRANSFER' with 9484 in description...")
print()

reader = csv.DictReader(lines[0:])
for i, row in enumerate(reader):
    if '9484' in row['description']:
        print(f"Row {i+1}: {row['date']} | {row['description']} | {row['amount']}")
        amount = float(row['amount'])
        if amount == 9484.0:
            print(f"  ❌ ERROR: Taking reference number 9484!")
        elif amount == 5500.0:
            print(f"  ✓ CORRECT: Amount is 5500")
        else:
            print(f"  Amount is {amount}")
