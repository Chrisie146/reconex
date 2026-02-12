import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf','rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

for amt in [17271.92, 17271.91, 6000.0, 3000.0]:
    print(f"\nRows with amount {amt}:")
    print(df[df['amount']==amt][['date','description','amount']].to_string(index=False))
