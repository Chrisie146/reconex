#!/usr/bin/env python
import requests
import json
import uuid

# Create a fresh test session
session_id = str(uuid.uuid4())
print(f"=== Test Session: {session_id[:8]}... ===\n")

# Step 1: Manually create transaction using save_parsed endpoint
print("=== Step 1: Adding Herotel Transaction ===")
payload = {
    "transactions": [
        {
            "date": "2026-01-01",
            "description": "HEROTEL (PTY) LTD",
            "amount": -849.0
        }
    ]
}
resp = requests.post(
    f"http://127.0.0.1:8000/save_parsed",
    json=payload
)
print(f"Status: {resp.status_code}")
result = resp.json()
manual_session = result['session_id']
print(f"Session created: {manual_session[:8]}...")
print(f"Transactions added: {result['transaction_count']}\n")

# Step 2: Upload invoice to the same session
print("=== Step 2: Uploading Invoice to Same Session ===")
invoice_pdf = "C:\\Users\\christopherm\\statementbur_python\\Invoice_23607174.pdf"
with open(invoice_pdf, 'rb') as f:
    files = {'file': f}
    resp = requests.post(
        f"http://127.0.0.1:8000/invoice/upload_file_auto?session_id={manual_session}",
        files=files
    )
    print(f"Status: {resp.status_code}")
    result = resp.json()
    invoice = result['invoice']
    print(f"Invoice: {invoice['supplier_name']}")
    print(f"  Amount: £{invoice['total_amount']}")
    print(f"  Date: {invoice['invoice_date']}\n")

# Step 3: Get transactions in session
print("=== Step 3: Verifying Transaction in Session ===")
resp = requests.get(
    f"http://127.0.0.1:8000/transactions?session_id={manual_session}"
)
data = resp.json()
print(f"Transactions in session: {data['count']}")
for txn in data['transactions'][:5]:
    print(f"  {txn['date']} - {txn['description']} - £{txn['amount']}")
print()

# Step 4: Run matching
print("=== Step 4: Running Invoice Matching ===")
resp = requests.post(
    f"http://127.0.0.1:8000/invoice/match?session_id={manual_session}"
)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Matches found: {data['count']}\n")

for m in data['matches']:
    print(f"Invoice: {m['invoice']['supplier_name']}")
    print(f"  Invoice Amount: £{m['invoice']['total_amount']}, Date: {m['invoice']['invoice_date']}")
    print(f"  Match Score: {m['confidence']} ({m['classification']})")
    print(f"  Explanation: {m['explanation']}")
    if m['transaction']:
        print(f"  ✓ MATCHED: {m['transaction']['date']} - {m['transaction']['description']} - £{abs(m['transaction']['amount'])}")
    else:
        print(f"  ✗ NO MATCH")
