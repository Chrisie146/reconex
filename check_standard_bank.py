#!/usr/bin/env python
"""Check Standard Bank output and find duplicates"""
import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
import pandas as pd
from io import StringIO

# Try to parse Standard Bank PDF
try:
    with open('Standard Bank.pdf', 'rb') as f:
        csv_bytes, year, note = pdf_to_csv_bytes(f.read())
    
    csv_text = csv_bytes.decode('utf-8')
    df = pd.read_csv(StringIO(csv_text))
    
    print(f"Total transactions: {len(df)}")
    print(f"NET TOTAL: R {df['amount'].sum():,.2f}")
    print()
    
    # Check for duplicates
    print("Checking for duplicates...")
    duplicates = df[df.duplicated(subset=['date', 'description', 'amount'], keep=False)]
    
    if len(duplicates) > 0:
        print(f"\nFound {len(duplicates)} duplicate rows:")
        print(duplicates.to_string())
    else:
        print("No exact duplicates found")
    
    print("\n\nAll transactions:")
    for idx, row in df.iterrows():
        print(f"{row['date']} | {row['description']:50} | {row['amount']:>15,.2f}")
        
except FileNotFoundError:
    print("Standard Bank.pdf not found")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
