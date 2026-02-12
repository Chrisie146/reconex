import sys
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
import io

with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

df = pd.read_csv(io.BytesIO(csv_bytes))

# Normalize amounts (remove spaces, convert to float)
df['amount_clean'] = df['amount'].astype(str).str.replace(' ', '').astype(float)

# Show all transactions with amounts between -0.01 and -5.00 (small fees)
small_fees = df[(df['amount_clean'] < 0) & (df['amount_clean'] >= -5.00)]
print(f"Small fee transactions (R0.01 to R5.00): {len(small_fees)}")
print("\nSample small fees:")
for idx, row in small_fees.head(10).iterrows():
    print(f"  {row['date']} | {row['description']:<50} | {row['amount']:>8}")

# Check for R1 fees specifically
r1_fees = df[df['amount_clean'] == -1.00]
print(f"\nR1.00 fees found: {len(r1_fees)}")
if len(r1_fees) > 0:
    print("Examples:")
    for idx, row in r1_fees.head(5).iterrows():
        print(f"  {row['date']} | {row['description']:<50} | {row['amount']:>8}")

# Check for SMS/other small fees
sms_fees = df[df['description'].str.contains('SMS', case=False, na=False)]
print(f"\nSMS fees found: {len(sms_fees)}")
if len(sms_fees) > 0:
    print("Sample SMS fees:")
    for idx, row in sms_fees.head(5).iterrows():
        print(f"  {row['date']} | {row['description']:<50} | {row['amount']:>8}")
