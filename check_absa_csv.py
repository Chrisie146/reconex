import sys
sys.path.insert(0, r'C:\Users\christopherm\statementbur_python\backend')

from services.pdf_parser import pdf_to_csv_bytes

pdf_path = r'C:\Users\christopherm\statementbur_python\Absa.pdf'

# Test PDF parsing
with open(pdf_path, 'rb') as f:
    content = f.read()

print("=== Testing ABSA PDF Parsing ===")
csv_bytes, statement_year, detected_bank = pdf_to_csv_bytes(content)

print(f"detected_bank= {detected_bank}")
print(f"statement_year= {statement_year}")
print(f"CSV size= {len(csv_bytes)} bytes")

# Count actual lines
csv_str = csv_bytes.decode('utf-8')
lines = csv_str.strip().split('\n')
print(f"Number of CSV lines: {len(lines)}")
print(f"Header: {lines[0]}")

# Show all rows
print("\n=== All CSV Rows ===")
for i, line in enumerate(lines[1:], 1):  # Skip header
    print(f"{i}: {line}")
