import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Check for duplicate date+description pairs with different amounts
print("Checking for duplicate (date, description) pairs with different amounts...")
dupes = df.groupby(['date', 'description']).size()
dupes_multi = dupes[dupes > 1]

if len(dupes_multi) > 0:
    print(f"\nFound {len(dupes_multi)} (date, description) pairs that appear multiple times:")
    for (date, desc), count in dupes_multi.items():
        rows = df[(df['date'] == date) & (df['description'] == desc)]
        print(f"\n{date} | {desc}")
        for idx, row in rows.iterrows():
            print(f"  Amount: {row['amount']}")
else:
    print("No duplicate (date, description) pairs!")

# Show summary
print(f"\n\nSummary:")
print(f"Total rows: {len(df)}")
print(f"Unique (date, description) pairs: {df.groupby(['date', 'description']).ngroups}")
print(f"Exact duplicates: {len(df[df.duplicated(keep=False)])}")
