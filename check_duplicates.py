import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Normalize amounts
df['amount_clean'] = df['amount'].astype(str).str.replace(' ', '').astype(float)

# Check 20/11/2025 DebiCheck transactions
rows_201125 = df[df['date'] == '20/11/2025']
print("Transactions on 20/11/2025:")
for idx, row in rows_201125.iterrows():
    print(f"  {row['date']} | {row['description']:<60} | {row['amount']:>10}")

# Check for duplicates
print("\n\nLooking for similar descriptions on same date:")
for date in df['date'].unique():
    date_rows = df[df['date'] == date]
    descriptions = date_rows['description'].values
    
    # Find rows with similar descriptions
    for i, desc1 in enumerate(descriptions):
        for j, desc2 in enumerate(descriptions):
            if i < j:
                # Check if descriptions are very similar (same core transaction)
                if desc1.split()[0:5] == desc2.split()[0:5]:  # First 5 words match
                    row1 = date_rows.iloc[i]
                    row2 = date_rows.iloc[j]
                    if row1['description'] != row2['description']:
                        print(f"\nPotential duplicate on {date}:")
                        print(f"  Row 1: {row1['description']:<60} | {row1['amount']:>10}")
                        print(f"  Row 2: {row2['description']:<60} | {row2['amount']:>10}")
