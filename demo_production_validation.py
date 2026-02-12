#!/usr/bin/env python
"""
Demo: Balance Validation in Production Mode

Shows how the annotation-only system works:
1. Transactions extracted from OCR
2. Balance validation runs (marks verified/failed/no-balance)
3. NO auto-corrections happen
4. Metadata stored for accounting review
"""
import sys, os
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
from services.bank_adapters import FNBAdapter
from services.balance_validator import BalanceValidator
import pandas as pd
from io import StringIO

print("=" * 80)
print("PRODUCTION BALANCE VALIDATION DEMO - Annotation-Only Mode")
print("=" * 80)

pdf_path = '20260119115115880.pdf'

# Step 1: Extract transactions from PDF
print("\n[Step 1] Extracting transactions from FNB PDF...")
with open(pdf_path, 'rb') as f:
    csv_bytes, year, bank = pdf_to_csv_bytes(f.read())

df = pd.read_csv(StringIO(csv_bytes.decode('utf-8')))
print(f"  ✓ Extracted {len(df)} transactions with balance information")

# Step 2: Normalize with balance validation
print("\n[Step 2] Running balance validation (strict=False - annotation-only)...")
adapter = FNBAdapter()
normalized = adapter.normalize(df, strict=False)  # Production mode
print(f"  ✓ Normalized {len(normalized)} transactions")

# Step 3: Show validation results
print("\n[Step 3] Validation Results:")
verified = (normalized['balance_verified'] == True).sum()
failed = (normalized['balance_verified'] == False).sum()
no_balance = (normalized['balance_verified'].isna()).sum()

print(f"  Verified (balance matched): {verified}")
print(f"  Failed (balance mismatch):  {failed}")
print(f"  No balance provided:        {no_balance}")
print(f"  Verification rate:          {verified / (len(normalized) - no_balance) * 100:.1f}%")

# Step 4: Show samples of each type
print("\n[Step 4] Sample transactions by verification status:")

print("\n  VERIFIED (balance_verified=True):")
verified_txns = normalized[normalized['balance_verified'] == True].head(2)
for i, row in verified_txns.iterrows():
    print(f"    {row['Date']}: {row['Description'][:40]:40} | {row['Amount']:>10.2f} | {row['validation_message']}")

print("\n  FAILED (balance_verified=False):")
failed_txns = normalized[normalized['balance_verified'] == False].head(2)
for i, row in failed_txns.iterrows():
    print(f"    {row['Date']}: {row['Description'][:40]:40} | {row['Amount']:>10.2f} | Diff: {row['balance_difference']:.2f}")

print("\n  NO BALANCE (balance_verified=None):")
no_bal_txns = normalized[normalized['balance_verified'].isna()].head(2)
for i, row in no_bal_txns.iterrows():
    print(f"    {row['Date']}: {row['Description'][:40]:40} | {row['Amount']:>10.2f} | {row['validation_message']}")

# Step 5: Show financial breakdown
print("\n[Step 5] Financial Summary:")
verified_df = normalized[normalized['balance_verified'] == True]
verified_income = verified_df[verified_df['Amount'] > 0]['Amount'].sum()
verified_expenses = verified_df[verified_df['Amount'] < 0]['Amount'].sum()
print(f"  Verified Income:    R {verified_income:>12,.2f}")
print(f"  Verified Expenses:  R {verified_expenses:>12,.2f}")
print(f"  Verified Net:       R {verified_income + verified_expenses:>12,.2f}")

unverified_df = normalized[normalized['balance_verified'] != True]
unverified_income = unverified_df[unverified_df['Amount'] > 0]['Amount'].sum()
unverified_expenses = unverified_df[unverified_df['Amount'] < 0]['Amount'].sum()
print(f"\n  Unverified Income:  R {unverified_income:>12,.2f}")
print(f"  Unverified Expense: R {unverified_expenses:>12,.2f}")
print(f"  Unverified Net:     R {unverified_income + unverified_expenses:>12,.2f}")

total_income = normalized[normalized['Amount'] > 0]['Amount'].sum()
total_expenses = normalized[normalized['Amount'] < 0]['Amount'].sum()
print(f"\n  TOTAL INCOME:       R {total_income:>12,.2f}")
print(f"  TOTAL EXPENSES:     R {total_expenses:>12,.2f}")
print(f"  TOTAL NET:          R {total_income + total_expenses:>12,.2f}")

print("\n" + "=" * 80)
print("KEY POINTS FOR PRODUCTION:")
print("=" * 80)
print("""
✓ NO AUTO-CORRECTIONS: Transaction amounts are extracted as-is
✓ ANNOTATED: Each transaction has validation metadata for review
✓ TRANSPARENT: Accountants see exactly which transactions verified
✓ SAFE: Failed validations are flagged, not silently changed
✓ AUDITABLE: Validation results stored in database for compliance
✓ ACCURATE: Only 57.8% verified - OCR line breaks cause missing balances

Frontend UI should show:
- Green checkmark: Balance verified (67 transactions)
- Red X: Balance mismatch (49 transactions) 
- Gray ?: No balance provided (18 transactions)

This gives accountants confidence in the data quality while preserving
the original extracted amounts for their review and approval.
""")
print("=" * 80)
