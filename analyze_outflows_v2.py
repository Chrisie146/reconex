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
    # Updated to include "external payment"
    if 'transfer' in desc_lower and 'credit card' in desc_lower:
        return 'Transfer'
    elif 'transfer' in desc_lower:
        return 'Transfer'
    elif 'digital' in desc_lower or 'immediate payment' in desc_lower or 'external payment' in desc_lower:
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

print('=== PARSED OUTFLOWS BY CATEGORY (UPDATED) ===')
summary = outflows.groupby('category')['amount'].sum().sort_values()
for cat, total in summary.items():
    print(f'{cat:<20} {total:>12.2f}')

print(f'\n{"Total parsed":<20} {outflows["amount"].sum():>12.2f}')

print('\n\n=== EXPECTED vs ACTUAL (UPDATED) ===')
expected = {
    'Transfer': -36800.83,
    'Digital Payments': -23698.00,
    'Debit Orders': -10439.59,
    'Card Payments': -403.60,
    'Prepaid': -227.00,
    'Fees': -146.10,
    'Capitec Pay': -74.00,
}

total_missing = 0
for cat, exp in expected.items():
    actual = outflows[outflows['category'] == cat]['amount'].sum()
    diff = exp - actual
    total_missing += diff
    print(f'{cat:<20} Expected: {exp:>10.2f} | Actual: {actual:>10.2f} | Missing: {diff:>10.2f}')

print(f'\nTotal missing: {total_missing:.2f}')
