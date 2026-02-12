"""Check which parsing path pdf_to_csv_bytes is using."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

# Patch the parsing functions to log when they're called
original_parse_business = None
original_parse_standard = None

def patched_parse_business(text, pdf, statement_year=None):
    print("[DEBUG] Called _parse_standard_bank_business_text")
    return original_parse_business(text, pdf, statement_year)

def patched_parse_standard(text, pdf):
    print("[DEBUG] Called _parse_standard_bank_text")
    return original_parse_standard(text, pdf)

import backend.services.pdf_parser as pdf_parser_mod
original_parse_business = pdf_parser_mod._parse_standard_bank_business_text
original_parse_standard = pdf_parser_mod._parse_standard_bank_text
pdf_parser_mod._parse_standard_bank_business_text = patched_parse_business
pdf_parser_mod._parse_standard_bank_text = patched_parse_standard

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = 'xxxxx0819_31.12.25.pdf'

with open(pdf_path, 'rb') as f:
    file_content = f.read()

print("Calling pdf_to_csv_bytes...")
csv_bytes, _, _ = pdf_to_csv_bytes(file_content)

print("\nDone. Checking CSV for 9484...")
import csv
csv_text = csv_bytes.decode('utf-8')
lines = csv_text.split('\n')

reader = csv.DictReader(lines)
for row in reader:
    if '9484' in row.get('description', ''):
        print(f"Found: {row['date']},{row['description']},{row['amount']}")
