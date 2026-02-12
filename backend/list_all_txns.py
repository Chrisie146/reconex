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

# Get all transactions
print("\n=== ALL TRANSACTIONS ===")
resp = requests.get(f"http://127.0.0.1:8000/transactions?session_id={session_id}")
data = resp.json()

for i, txn in enumerate(data['transactions']):
    print(f"{i+1}. {txn['date']} | £{txn['amount']:>8} | {txn['description']}")
