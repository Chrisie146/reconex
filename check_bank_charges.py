import sys
sys.path.insert(0, 'backend')

from services.pdf_parser import pdf_to_csv_bytes
from io import BytesIO

with open('FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf', 'rb') as f:
    pdf_bytes = f.read()

csv_bytes = pdf_to_csv_bytes(pdf_bytes)
csv_text = csv_bytes[0].decode('utf-8')

print("\n=== Looking for small bank charges (under R 10) ===")
for line in csv_text.strip().split('\n')[1:]:  # Skip header
    parts = line.split(',')
    if len(parts) >= 4:
        amount = parts[3].strip()
        try:
            amt_val = float(amount)
            if abs(amt_val) < 10:
                print(f"Small amount: {amount} | Date: {parts[0]} | Desc: {parts[2][:50]}")
        except:
            pass

print("\n=== All amounts between 1 and 5 ===")
for line in csv_text.strip().split('\n')[1:]:
    parts = line.split(',')
    if len(parts) >= 4:
        amount = parts[3].strip()
        try:
            amt_val = abs(float(amount))
            if 1 <= amt_val <= 5:
                print(f"Amount: {amount} | Desc: {parts[2][:60]}")
        except:
            pass
