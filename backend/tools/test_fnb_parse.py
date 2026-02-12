import sys
sys.path.insert(0, r'c:\Users\christopherm\statementbur_python\backend')

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = r'c:\Users\christopherm\statementbur_python\FNB_ASPIRE_CURRENT_ACCOUNT_132-1.pdf'

with open(pdf_path, 'rb') as f:
    pdf_content = f.read()

try:
    csv_bytes = pdf_to_csv_bytes(pdf_content)
    csv_text = csv_bytes.decode('utf-8')
    
    print("SUCCESS! Parsed FNB PDF:")
    print("="*60)
    lines = csv_text.split('\n')
    print(f"Total rows: {len(lines) - 1}")  # -1 for header
    print("\nFirst 30 rows:")
    for line in lines[:30]:
        print(line)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
