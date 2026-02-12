#!/usr/bin/env python
import requests
import os

# Upload bank statement
bank_pdf = "C:\\Users\\christopherm\\statementbur_python\\FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf"

print("=== Uploading Bank Statement ===")
with open(bank_pdf, 'rb') as f:
    files = {'file': f}
    resp = requests.post(
        f"http://127.0.0.1:8000/upload_pdf",
        files=files
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    session_id = data['session_id']
    print(f"Session: {session_id}")
    print(f"Transactions: {data['transaction_count']}")

# Get transactions
print("\n=== Getting Transactions ===")
resp = requests.get(
    f"http://127.0.0.1:8000/transactions?session_id={session_id}"
)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Found {data['count']} transactions")

# Look for Herotel
print("\nSearching for Herotel transactions:")
for txn in data['transactions']:
    if 'herotel' in txn['description'].lower():
        print(f"  ID: {txn['id']}, Date: {txn['date']}, Desc: {txn['description']}, Amount: {txn['amount']}")

# Upload invoice
print("\n=== Uploading Invoice ===")
invoice_pdf = "C:\\Users\\christopherm\\statementbur_python\\Invoice_23607174.pdf"
with open(invoice_pdf, 'rb') as f:
    files = {'file': f}
    resp = requests.post(
        f"http://127.0.0.1:8000/invoice/upload_file_auto?session_id={session_id}",
        files=files
    )
    print(f"Status: {resp.status_code}")
    result = resp.json()
    print(f"Invoice: {result['invoice']['supplier_name']}, Amount: {result['invoice']['total_amount']}, Date: {result['invoice']['invoice_date']}")
    print(f"Suggested match score: {result['suggested_match']['score']}")
    print(f"Explanation: {result['suggested_match']['explanation']}")

# Run matching
print("\n=== Running Invoice Matching ===")
resp = requests.post(
    f"http://127.0.0.1:8000/invoice/match?session_id={session_id}"
)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Found {data['count']} matches")
for m in data['matches']:
    print(f"\nInvoice: {m['invoice']['supplier_name']}")
    print(f"  Score: {m['confidence']} ({m['classification']})")
    print(f"  Explanation: {m['explanation']}")
    if m['transaction']:
        print(f"  Matched Txn: {m['transaction']['date']} - {m['transaction']['description']} - {m['transaction']['amount']}")
