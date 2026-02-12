import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf', 'rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

# Check for Judy Digital Payments entries
judy = df[df['description'].str.contains('Judy', case=False, na=False)]
print('=== JUDY ENTRIES ===')
print(f'Found {len(judy)} entries')
for idx, row in judy.sort_values('date').iterrows():
    desc = row['description'][:50]
    print(f"{row['date']} {row['amount']:>10.2f} {desc}")

# Check for Chris entries
chris = df[df['description'].str.contains('Chris', case=False, na=False)]
print(f'\n\n=== CHRIS ENTRIES ===')
print(f'Found {len(chris)} entries')
for idx, row in chris.sort_values('date').iterrows():
    desc = row['description'][:50]
    print(f"{row['date']} {row['amount']:>10.2f} {desc}")

# Look specifically for 25/10 and 28/11 Judy/Chris payments (the large ones)
print(f'\n\n=== 25/10 TRANSACTIONS ===')
oct25 = df[df['date'] == '25/10/2025']
for idx, row in oct25.iterrows():
    desc = row['description'][:50]
    print(f"{row['date']} {row['amount']:>10.2f} {desc}")

print(f'\n\n=== 28/11 TRANSACTIONS ===')
nov28 = df[df['date'] == '28/11/2025']
for idx, row in nov28.iterrows():
    desc = row['description'][:50]
    print(f"{row['date']} {row['amount']:>10.2f} {desc}")
