import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check all DebiCheck transactions with 3146
print("All DebiCheck transactions with 3146:")
debicheck_3146 = df[(df['description'].str.contains('DebiCheck', case=False, na=False)) & 
                     (df['amount'].astype(str).str.contains('3146|3149', na=False))]
for idx, row in debicheck_3146.iterrows():
    print(f"  {row['date']} | {row['description']:<60} | {row['amount']:>10}")

# Check for any (Fee) rows on 20/11
print("\n\n(Fee) rows on 20/11/2025:")
fee_rows_201125 = df[(df['date'] == '20/11/2025') & (df['description'].str.contains('\\(Fee\\)', regex=True, na=False))]
for idx, row in fee_rows_201125.iterrows():
    print(f"  {row['description']:<60} | {row['amount']:>10}")
