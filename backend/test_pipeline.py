import sys
sys.path.insert(0, '.')
from services.pdf_parser import pdf_to_csv_bytes
from services.parser import validate_csv, normalize_csv

with open('../FNB_PREMIER_CURRENT_ACCOUNT_170.pdf', 'rb') as f:
    content = f.read()

csv_bytes, year = pdf_to_csv_bytes(content)
print('Step 1: PDF extraction - OK')

is_valid, msg = validate_csv(csv_bytes)
status = 'OK' if is_valid else 'FAILED'
print(f'Step 2: CSV validation - {status}')
if not is_valid:
    print(f'  Error: {msg}')
else:
    print(f'  Message: {msg}')

normalized, err_msg, skipped = normalize_csv(csv_bytes, year)
print(f'Step 3: CSV normalization - {len(normalized)} transactions')
if err_msg:
    print(f'  Warning: {err_msg}')
if skipped:
    print(f'  Skipped: {len(skipped)} rows')
    
if normalized:
    print('\nFirst 3 transactions:')
    for txn in normalized[:3]:
        print(f'  {txn["date"]} | {txn["description"][:40]} | {txn["amount"]}')
