import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.pdf_parser import pdf_to_csv_bytes

# Load Standard Bank PDF
pdf_path = r'Bank_statements\Standard bank.pdf'
with open(pdf_path, 'rb') as f:
    file_content = f.read()

# Parse PDF
csv_bytes, year, bank = pdf_to_csv_bytes(file_content)
csv_str = csv_bytes.decode('utf-8')
lines = csv_str.split('\n')

print(f"Bank: {bank}")
print(f"Total rows: {len(lines) - 1}")
print("="*80)

# Calculate net balance
total = 0.0
transaction_count = 0

for i, line in enumerate(lines[1:], start=2):  # Skip header
    if not line.strip():
        continue
    
    parts = line.split(',')
    if len(parts) >= 3:
        try:
            amount = float(parts[2])
            total += amount
            transaction_count += 1
        except ValueError:
            print(f"Warning: Could not parse amount at line {i}: {line}")

print(f"Transaction count: {transaction_count}")
print(f"Net balance: R{total:,.2f}")
print("="*80)

expected = 988372.55
difference = abs(total - expected)

if abs(difference) < 0.01:
    print(f"✓ PASS: Net balance matches expected value")
    print(f"  Expected: R{expected:,.2f}")
    print(f"  Got:      R{total:,.2f}")
    print(f"  Difference: R{difference:,.2f}")
else:
    print(f"✗ FAIL: Net balance does not match")
    print(f"  Expected: R{expected:,.2f}")
    print(f"  Got:      R{total:,.2f}")
    print(f"  Difference: R{abs(total - expected):,.2f}")
