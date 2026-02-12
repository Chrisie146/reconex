#!/usr/bin/env python
import requests

# Upload bank statement
bank_pdf = "C:\\Users\\christopherm\\statementbur_python\\FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf"

print("=== Uploading Bank Statement ===")
with open(bank_pdf, 'rb') as f:
    files = {'file': f}
    resp = requests.post("http://127.0.0.1:8000/upload_pdf", files=files)
    data = resp.json()
    session_id = data['session_id']
    print(f"Session: {session_id}")

# Get all transactions
print("\n=== All Transactions ===")
resp = requests.get(f"http://127.0.0.1:8000/transactions?session_id={session_id}")
data = resp.json()
print(f"Total: {data['count']}")

# Look for large transactions (849 or close to it)
print("\n=== Transactions near £849 ===")
for txn in data['transactions']:
    amt = float(txn['amount'])
    if 800 < amt < 900 or (700 < amt < 750 and 'herotel' in txn['description'].lower()):
        print(f"  {txn['date']} - {txn['description']} - £{amt}")

# Look for Herotel, Magstec, or similar
print("\n=== Transactions with specific keywords ===")
keywords = ['herotel', 'magstec', 'credit', 'hotel']
for kw in keywords:
    print(f"\n{kw.upper()}:")
    found = False
    for txn in data['transactions']:
        if kw in txn['description'].lower():
            print(f"  {txn['date']} - {txn['description']} - £{txn['amount']}")
            found = True
    if not found:
        print(f"  (none found)")
