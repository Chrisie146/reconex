"""Force re-generate the CSV using the actual normalize_csv flow."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = 'xxxxx0819_31.12.25.pdf'

with open(pdf_path, 'rb') as f:
    file_content = f.read()

# Use pdf_to_csv_bytes to generate CSV bytes
csv_bytes, _, _ = pdf_to_csv_bytes(file_content)

# Save
with open('debug_out_standard_bank_fresh.csv', 'wb') as f:
    f.write(csv_bytes)

print("[OK] Regenerated CSV with adapter")

# Check 9484
import csv
csv_text = csv_bytes.decode('utf-8')
lines = csv_text.split('\n')

reader = csv.DictReader(lines)
for i, row in enumerate(reader):
    if '9484' in row.get('description', ''):
        print(f"\nFound 9484:")
        print(f"  Date: {row['date']}")
        print(f"  Description: {row['description']}")
        print(f"  Amount: {row['amount']}")
        amt = float(row['amount'])
        if amt == 5500:
            print(f"  ✓ CORRECT!")
        elif amt == 9484:
            print(f"  ❌ WRONG!")
