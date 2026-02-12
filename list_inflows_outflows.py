import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf', 'rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

print('=== ALL INFLOWS (positive amounts) ===')
inflows = df[df['amount'] > 0].sort_values('amount', ascending=False)
print(inflows[['date', 'description', 'amount']].to_string(index=False))
print(f'\nTotal inflows: {inflows["amount"].sum():.2f}')
print(f'Count inflows: {len(inflows)}')

print('\n\n=== ALL OUTFLOWS (negative amounts, sorted by amount) ===')
outflows = df[df['amount'] < 0].sort_values('amount')
for idx, row in outflows.iterrows():
    print(f"{row['date']} {row['description'][:50]:<50} {row['amount']:>10.2f}")
print(f'\nTotal outflows: {outflows["amount"].sum():.2f}')
print(f'Count outflows: {len(outflows)}')

print('\n\n=== EXPECTED vs ACTUAL ===')
print(f'Expected money in: 70865.56')
print(f'Actual money in: {inflows["amount"].sum():.2f}')
print(f'Missing inflows: {70865.56 - inflows["amount"].sum():.2f}')
print()
print(f'Expected money out: -71789.12')
print(f'Actual money out: {outflows["amount"].sum():.2f}')
print(f'Missing outflows: {-71789.12 - outflows["amount"].sum():.2f}')
