import sys
sys.path.insert(0, r'C:\Users\christopherm\statementbur_python\backend')
from services.pdf_parser import pdf_to_csv_bytes
from services.parser import normalize_csv

pdf_path = r'C:\Users\christopherm\statementbur_python\Absa.pdf'

with open(pdf_path, 'rb') as f:
    content = f.read()

csv_bytes, statement_year, detected_bank = pdf_to_csv_bytes(content)
result = normalize_csv(csv_bytes, statement_year=statement_year, forced_bank=detected_bank)
transactions = result[0] if isinstance(result, tuple) else result

# Sort by date for easier review
txns = sorted(transactions, key=lambda t: t['date'])

print("=== ALL ABSA TRANSACTIONS ===\n")
for i, t in enumerate(txns, 1):
    sign = "IN " if t['amount'] > 0 else "OUT"
    print(f"{i:2}. {t['date']} | {sign} | R{abs(t['amount']):>12,.2f} | {t['description']}")

print(f"\n\nTotal rows: {len(txns)}")
print(f"Income count: {sum(1 for t in txns if t['amount'] > 0)}")
print(f"Expense count: {sum(1 for t in txns if t['amount'] < 0)}")
