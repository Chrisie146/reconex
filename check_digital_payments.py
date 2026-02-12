import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check 11/01/2026 transactions
rows_110126 = df[df['date'] == '11/01/2026']
print("Transactions on 11/01/2026:")
for idx, row in rows_110126.iterrows():
    print(f"  {row['date']} | {row['description']:<50} | {row['amount']:>10}")

# Check for Digital Payment entries
digital_payments = df[df['description'].str.contains('Digital', case=False, na=False)]
print(f"\nTotal Digital Payment transactions: {len(digital_payments)}")
print("Sample Digital Payments:")
for idx, row in digital_payments.head(10).iterrows():
    print(f"  {row['date']} | {row['description']:<50} | {row['amount']:>10}")
