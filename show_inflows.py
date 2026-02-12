import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf', 'rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

inflows = df[df['amount'] > 0].sort_values('amount', ascending=False)
print('=== ALL INFLOWS ===')
for idx, row in inflows.iterrows():
    desc = row['description'][:45]
    print(f"{row['date']} {desc:<45} {row['amount']:>10.2f}")

print(f'\nTotal inflows: {inflows["amount"].sum():.2f}')
print(f'Expected: 70865.56')
print(f'Missing: {70865.56 - inflows["amount"].sum():.2f}')
