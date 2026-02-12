import sys
import io
import pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf','rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))

df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

print('Rows:', len(df))
print('Sum:', df['amount'].sum())
print('\nSample head:')
print(df.head(10).to_string(index=False))
print('\nSample tail:')
print(df.tail(10).to_string(index=False))

print('\nSalary rows:')
print(df[df['description'].str.contains('Salary', case=False, na=False)][['date','description','amount']].to_string(index=False))

# Rows with 'balance' or 'closing' in description
print('\nRows mentioning balance:')
print(df[df['description'].str.contains('balance', case=False, na=False)][['date','description','amount']].to_string(index=False))

# Look for unusually large amounts
print('\nLarge positive amounts (>1000):')
print(df[df['amount']>1000][['date','description','amount']].to_string(index=False))

# Check for very small amounts appearing many times
print('\nVery small abs amounts (<1):')
print(df[df['amount'].abs()<1][['date','description','amount']].head(20).to_string(index=False))
