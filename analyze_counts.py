import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf','rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))

df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

# Group by date, amount
counts = df.groupby(['date','amount']).size().reset_index(name='count').sort_values('count', ascending=False)
print(counts.head(30).to_string(index=False))

# Show rows for the largest repeated items
repeated = counts[counts['count']>1]
if not repeated.empty:
    print('\nRepeated groups:')
    for _, r in repeated.iterrows():
        date, amount = r['date'], r['amount']
        print(f"\nGroup: {date} {amount} appears {r['count']} times")
        print(df[(df['date']==date) & (df['amount']==amount)][['date','description','amount']].to_string(index=False))
else:
    print('\nNo repeated date+amount groups found')
