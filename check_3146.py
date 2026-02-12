import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check for the 3146 transaction on 20/11
print("20/11/2025 transactions with 3146:")
rows_3146 = df[(df['date'] == '20/11/2025') & (df['amount'].astype(str).str.contains('3146', na=False))]
for idx, row in rows_3146.iterrows():
    print(f"  Date: {row['date']}")
    print(f"  Description: {row['description']}")
    print(f"  Amount: {row['amount']}")
    print()

# Check for ALL transactions with that amount 
print("\nAll transactions with amount 3146:")
all_3146 = df[df['amount'].astype(str).str.contains('3146', na=False)]
for idx, row in all_3146.iterrows():
    print(f"  {row['date']} | {row['description']:<60} | {row['amount']:>10}")
