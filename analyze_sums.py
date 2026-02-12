import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf','rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

pos = df[df['amount']>0]['amount'].sum()
neg = df[df['amount']<0]['amount'].sum()
print('Total rows:', len(df))
print('Total sum:', df['amount'].sum())
print('Positive sum:', pos)
print('Negative sum:', neg)

print('\nTop positive amounts grouped:')
print(df[df['amount']>0].groupby(['date','amount']).size().reset_index(name='count').sort_values(['amount','count'], ascending=[False,False]).head(30).to_string(index=False))

print('\nTop negative amounts grouped:')
print(df[df['amount']<0].groupby(['date','amount']).size().reset_index(name='count').sort_values(['amount','count'], ascending=[True,False]).head(30).to_string(index=False))
