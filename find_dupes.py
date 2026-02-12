import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf', 'rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))

# Find exact duplicates
dupes = df[df.duplicated(subset=['date', 'description', 'amount'], keep=False)]
print(f'Exact duplicates (date, desc, amount): {len(dupes)}')
if len(dupes) > 0:
    print('\nDuplicate rows:')
    for idx, row in dupes.sort_values(['date', 'description', 'amount']).iterrows():
        desc = row['description'][:50]
        print(f"{row['date']} {row['amount']} {desc}")
