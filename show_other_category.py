import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf', 'rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

# Categorize outflows
outflows = df[df['amount'] < 0].copy()

def categorize(desc):
    desc_lower = desc.lower()
    if 'transfer' in desc_lower and 'credit card' in desc_lower:
        return 'Transfer'
    elif 'transfer' in desc_lower:
        return 'Transfer'
    elif 'digital' in desc_lower or 'immediate payment' in desc_lower:
        return 'Digital Payments'
    elif 'debicheck' in desc_lower or 'eft' in desc_lower or 'debit order' in desc_lower:
        return 'Debit Orders'
    elif 'card' in desc_lower and 'payment' in desc_lower:
        return 'Card Payments'
    elif 'prepaid' in desc_lower or 'cellphone' in desc_lower:
        return 'Prepaid'
    elif 'fee' in desc_lower or 'notification' in desc_lower:
        return 'Fees'
    elif 'capitec pay' in desc_lower:
        return 'Capitec Pay'
    else:
        return 'Other'

outflows['category'] = outflows['description'].apply(categorize)

print('=== ITEMS IN "OTHER" CATEGORY ===')
other = outflows[outflows['category'] == 'Other'].sort_values('amount')
for idx, row in other.iterrows():
    print(f"{row['date']} {row['description'][:60]:<60} {row['amount']:>10.2f}")

print(f'\nTotal Other: {other["amount"].sum():.2f}')
