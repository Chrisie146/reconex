import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check 20/11/2025 Gems Medical Aid
print("Gems Medical Aid transactions on 20/11/2025:")
gems_rows = df[(df['date'] == '20/11/2025') & (df['description'].str.contains('Gems Medical', case=False, na=False))]
for idx, row in gems_rows.iterrows():
    print(f"  {row['date']} | {row['description']:<60} | {row['amount']:>10}")

# Check 20/11/2025 DebiCheck
print("\n\nDebiCheck Debit Order on 20/11/2025:")
debicheck_rows = df[(df['date'] == '20/11/2025') & (df['description'].str.contains('DebiCheck', case=False, na=False))]
for idx, row in debicheck_rows.iterrows():
    print(f"  {row['date']} | {row['description']:<60} | {row['amount']:>10}")

# Verify no exact duplicates
print(f"\n\nTotal rows: {len(df)}")
dupes = df[df.duplicated(keep=False)]
print(f"Exact duplicates: {len(dupes)}")
