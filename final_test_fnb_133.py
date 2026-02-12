"""Final verification that date parsing is fixed"""

import sys
import csv
import io
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = 'FNB_ASPIRE_CURRENT_ACCOUNT_133.pdf'

print(f"Testing: {pdf_path}")
print("=" * 80)

# Read and parse the PDF
with open(pdf_path, 'rb') as f:
    file_content = f.read()

csv_bytes, statement_year, bank = pdf_to_csv_bytes(file_content)

# Parse CSV to get transactions
csv_text = csv_bytes.decode('utf-8')
csv_reader = csv.DictReader(io.StringIO(csv_text))
result = list(csv_reader)

print(f"Parsed {len(result)} transactions (Year: {statement_year}, Bank: {bank})")
print("\n" + "=" * 80)
print("RESULT:")
print("=" * 80)

# Check December dates
december_rows = [row for row in result if ' Dec 2' in row['date']]
december_2025 = [row for row in december_rows if ' Dec 2025' in row['date']]
december_2026 = [row for row in december_rows if ' Dec 2026' in row['date']]

# Check January dates
january_rows = [row for row in result if ' Jan 2' in row['date']]
january_2025 = [row for row in january_rows if ' Jan 2025' in row['date']]
january_2026 = [row for row in january_rows if ' Jan 2026' in row['date']]

print(f"December 2025 transactions: {len(december_2025)} ✓")
print(f"December 2026 transactions: {len(december_2026)} {'✗ PROBLEM!' if december_2026 else '✓'}")
print(f"\nJanuary 2025 transactions: {len(january_2025)} {'✗ PROBLEM!' if january_2025 else '✓'}")
print(f"January 2026 transactions: {len(january_2026)} ✓")

if december_2026:
    print(f"\nProblematic December 2026 entries:")
    for row in december_2026[:3]:
        print(f"  {row['date']}: {row['description'][:50]}")

if january_2025:
    print(f"\nProblematic January 2025 entries:")
    for row in january_2025[:3]:
        print(f"  {row['date']}: {row['description'][:50]}")

print("\n" + "=" * 80)
if not december_2026 and not january_2025:
    print("✓ SUCCESS! All dates are correctly parsed:")
    print("  - December transactions are marked as 2025")
    print("  - January transactions are marked as 2026")
else:
    print("✗ FAILED! There are still date parsing issues")
