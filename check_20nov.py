import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check all 20/11/2025 rows
print("ALL transactions on 20/11/2025:")
rows_201125 = df[df['date'] == '20/11/2025']
for idx, row in rows_201125.iterrows():
    print(f"  {row['description']:<60} | {row['amount']:>10}")

print(f"\nTotal on 20/11: {len(rows_201125)}")
