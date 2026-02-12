#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))
print(f'Total rows: {len(df)}')
print(f'Unique (date, description): {len(df.groupby(["date", "description"]))}')
print(f'Unique (date, description, amount): {len(df.groupby(["date", "description", "amount"]))}')

# Check for exact duplicates
duplicates = df[df.duplicated(subset=['date', 'description', 'amount'], keep=False)]
print(f'\nExact duplicates: {len(duplicates)}')
if len(duplicates) > 0:
    print("Duplicate rows:")
    print(duplicates[['date', 'description', 'amount']].to_string())

# Check transactions per date
print(f'\nTransactions by date:')
by_date = df.groupby('date').size().sort_values(ascending=False)
print(by_date.head(10))

# Verify 19/12 has 4 transactions
print(f'\n19/12/2025 transactions: {len(df[df["date"] == "19/12/2025"])}')
