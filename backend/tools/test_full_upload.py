import sys
sys.path.insert(0, r'c:\Users\christopherm\statementbur_python\backend')

from services.pdf_parser import pdf_to_csv_bytes
from services.parser import validate_csv, normalize_csv

pdf_path = r'c:\Users\christopherm\statementbur_python\FNB_ASPIRE_CURRENT_ACCOUNT_132-1.pdf'

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

try:
    print("Step 1: Parse PDF to CSV...")
    csv_bytes, statement_year = pdf_to_csv_bytes(pdf_content)
    print(f"✓ PDF parsed successfully (statement year: {statement_year})\n")
    
    print("Step 2: Validate CSV...")
    is_valid, error_msg = validate_csv(csv_bytes)
    print(f"Valid: {is_valid}")
    if error_msg:
        print(f"Error: {error_msg}")
    print()
    
    print("Step 3: Normalize transactions...")
    normalized_transactions, parse_warnings, skipped_rows = normalize_csv(csv_bytes, statement_year)
    print(f"✓ Found {len(normalized_transactions)} transactions")
    
    if parse_warnings:
        print(f"\nWarnings: {parse_warnings}")
    
    if skipped_rows:
        print(f"\nSkipped {len(skipped_rows)} rows:")
        for skip in skipped_rows[:5]:
            print(f"  Row {skip['row']}: {skip['reason']}")
    
    print("\nFirst 10 transactions:")
    for i, txn in enumerate(normalized_transactions[:10], 1):
        print(f"{i}. {txn['date']} | {txn['description'][:40]:40s} | {txn['amount']:10.2f}")
    
    print("\n✓ Full upload flow works!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
