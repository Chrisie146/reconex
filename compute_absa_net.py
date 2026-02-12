import sys
sys.path.insert(0, r'C:\Users\christopherm\statementbur_python\backend')
from services.pdf_parser import pdf_to_csv_bytes
from services.parser import normalize_csv

pdf_path = r'C:\Users\christopherm\statementbur_python\Absa.pdf'

target = 130933.73

with open(pdf_path, 'rb') as f:
    content = f.read()

csv_bytes, statement_year, detected_bank = pdf_to_csv_bytes(content)
print('detected_bank=', detected_bank)
print('statement_year=', statement_year)

result = normalize_csv(csv_bytes, statement_year=statement_year, forced_bank=detected_bank)
# normalize_csv returns (transactions, warnings, skipped_rows, detected_bank)
if isinstance(result, tuple) and len(result) >= 1:
    transactions = result[0]
else:
    transactions = result

# transactions could be list of dicts
if not transactions:
    print('No transactions after normalization')
    sys.exit(1)

income = sum(t['amount'] for t in transactions if t['amount'] > 0)
expenses = sum(-t['amount'] for t in transactions if t['amount'] < 0)
net = income - expenses

print(f'Total income: {income:.2f}')
print(f'Total expenses: {expenses:.2f}')
print(f'Net movement: {net:.2f}')
print(f'Target: {target:.2f}')
print(f'Difference (net - target): {net - target:.2f}')
