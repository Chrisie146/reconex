import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check salary payments
print("Salary/Payment transactions:")
salary_rows = df[df['description'].str.contains('Payment Received|Salary', case=False, na=False)]
for idx, row in salary_rows.iterrows():
    print(f"  {row['date']} | {row['description']:<60} | {row['amount']:>10}")

# Check for exact duplicates
dupes = df[df.duplicated(keep=False)]
print(f"\n\nTotal rows: {len(df)}")
print(f"Exact duplicates: {len(dupes)}")

# Check for (date, amount) duplicates
date_amount_dupes = df.groupby(['date', 'amount']).size()
date_amount_dupes_multi = date_amount_dupes[date_amount_dupes > 1]
print(f"(Date, Amount) duplicates: {len(date_amount_dupes_multi)}")
if len(date_amount_dupes_multi) > 0:
    print("\nDuplicate (date, amount) pairs:")
    for (date, amount), count in date_amount_dupes_multi.items():
        print(f"  {date} | {amount} (appears {count} times)")
