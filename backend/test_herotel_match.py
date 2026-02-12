#!/usr/bin/env python
import requests
import uuid

# Use a consistent session ID
session_id = "test_herotel_" + str(uuid.uuid4())[:8]
print(f"Using session: {session_id}\n")

# 1. Upload bank statement
print("=== 1. Uploading Bank Statement ===")
bank_pdf = "C:\\Users\\christopherm\\statementbur_python\\FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf"
with open(bank_pdf, 'rb') as f:
    files = {'file': f}
    resp = requests.post(
        f"http://127.0.0.1:8000/upload_pdf?session_id={session_id}",
        files=files
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    actual_session = data.get('session_id', session_id)
    print(f"Actual session: {actual_session}")
    print(f"Transactions uploaded: {data['transaction_count']}")

# 2. Get transactions (verify Herotel exists)
print("\n=== 2. Looking for Herotel Transaction ===")
resp = requests.get(
    f"http://127.0.0.1:8000/transactions?session_id={actual_session}"
)
data = resp.json()
print(f"Total transactions in session: {data['count']}")

herotel_txn = None
for txn in data['transactions']:
    if 'herotel' in txn['description'].lower():
        print(f"Found: {txn['date']} - {txn['description']} - £{txn['amount']}")
        herotel_txn = txn
        break

if not herotel_txn:
    print("WARNING: No Herotel transaction found in this session!")

# 3. Upload invoice
print("\n=== 3. Uploading Invoice ===")
invoice_pdf = "C:\\Users\\christopherm\\statementbur_python\\Invoice_23607174.pdf"
with open(invoice_pdf, 'rb') as f:
    files = {'file': f}
    resp = requests.post(
        f"http://127.0.0.1:8000/invoice/upload_file_auto?session_id={actual_session}",
        files=files
    )
    print(f"Status: {resp.status_code}")
    result = resp.json()
    invoice = result['invoice']
    print(f"Invoice: {invoice['supplier_name']}")
    print(f"  Amount: £{invoice['total_amount']}")
    print(f"  Date: {invoice['invoice_date']}")
    print(f"  Number: {invoice['invoice_number']}")

# 4. Run matching
print("\n=== 4. Running Invoice Matching ===")
resp = requests.post(
    f"http://127.0.0.1:8000/invoice/match?session_id={actual_session}"
)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Matches found: {data['count']}\n")

for m in data['matches']:
    print(f"Invoice: {m['invoice']['supplier_name']}")
    print(f"  Amount: £{m['invoice']['total_amount']}, Date: {m['invoice']['invoice_date']}")
    print(f"  Match Score: {m['confidence']} ({m['classification']})")
    print(f"  Explanation: {m['explanation']}")
    if m['transaction']:
        print(f"  Matched Txn: {m['transaction']['date']} - {m['transaction']['description']} - £{m['transaction']['amount']}")
    else:
        print(f"  Matched Txn: None")
