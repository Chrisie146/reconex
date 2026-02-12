import sys
# Ensure backend package is importable
sys.path.insert(0, 'backend')
import io
import pandas as pd
from backend.services.pdf_parser import pdf_to_csv_bytes

# Open the Capitec PDF and parse it
with open('Capitec.pdf', 'rb') as f:
    csv_bytes, _ = pdf_to_csv_bytes(f.read())

# Read the parsed CSV into a DataFrame
df = pd.read_csv(io.BytesIO(csv_bytes))

# Print the first few rows to verify structure
print("First few rows of the parsed data:")
print(df.head())

# Extract and print the opening and closing balances
opening_balance = df['amount'].iloc[0]
closing_balance = df['amount'].iloc[-1]
print(f"Opening balance: {opening_balance}")
print(f"Closing balance: {closing_balance}")