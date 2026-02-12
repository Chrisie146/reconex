import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))
print(f'Total rows: {len(df)}')
print(f'Unique (date, description) pairs: {df.groupby(["date", "description"]).ngroups}')
print(f'Unique (date, description, amount) triplets: {df.groupby(["date", "description", "amount"]).ngroups}')

# Check for exact duplicates
dupes = df[df.duplicated(keep=False)]
print(f'Exact duplicates: {len(dupes)}')

# Show date range
print(f'\nDate range: {df["date"].min()} to {df["date"].max()}')
print(f'Number of unique dates: {df["date"].nunique()}')
