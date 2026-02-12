#!/usr/bin/env python
"""
End-to-end test simulating the full user flow:
1. Upload bank statement (creates new session with transactions)
2. Upload invoice to that session
3. Run matching
4. Confirm the match works correctly
"""
import requests
import uuid

print("=" * 70)
print("END-TO-END TEST: Bank Statement + Invoice Matching")
print("=" * 70)

# Step 1: Upload bank statement
print("\n[1/4] Uploading Bank Statement (FNB_ASPIRE_CURRENT_ACCOUNT_132.pdf)...")
bank_pdf = "C:\\Users\\christopherm\\statementbur_python\\FNB_ASPIRE_CURRENT_ACCOUNT_132.pdf"
with open(bank_pdf, 'rb') as f:
    resp = requests.post("http://127.0.0.1:8000/upload_pdf", files={'file': f})
    
if resp.status_code != 200:
    print(f"❌ FAILED: {resp.status_code}")
    print(resp.json())
    exit(1)

result = resp.json()
session_id = result['session_id']
txn_count = result['transaction_count']
print(f"✓ SUCCESS")
print(f"  Session: {session_id[:8]}...")
print(f"  Transactions: {txn_count}")

# Step 2: Check if Herotel transaction exists
print("\n[2/4] Checking for Herotel Transaction...")
resp = requests.get(f"http://127.0.0.1:8000/transactions?session_id={session_id}")
data = resp.json()

herotel_found = False
for txn in data['transactions']:
    if 'herotel' in txn['description'].lower():
        herotel_found = True
        print(f"✓ FOUND: {txn['date']} - {txn['description']} - £{txn['amount']}")
        break

if not herotel_found:
    print(f"⚠ WARNING: No Herotel transaction found in statement")
    print(f"  Total transactions: {data['count']}")
    if data['count'] > 0:
        print(f"  Sample transactions:")
        for txn in data['transactions'][:3]:
            print(f"    - {txn['date']} - {txn['description']} - £{txn['amount']}")

# Step 3: Upload Invoice
print("\n[3/4] Uploading Invoice (Invoice_23607174.pdf)...")
invoice_pdf = "C:\\Users\\christopherm\\statementbur_python\\Invoice_23607174.pdf"
with open(invoice_pdf, 'rb') as f:
    resp = requests.post(
        f"http://127.0.0.1:8000/invoice/upload_file_auto?session_id={session_id}",
        files={'file': f}
    )

if resp.status_code != 200:
    print(f"❌ FAILED: {resp.status_code}")
    print(resp.json())
    exit(1)

result = resp.json()
invoice = result['invoice']
print(f"✓ SUCCESS")
print(f"  Supplier: {invoice['supplier_name']}")
print(f"  Amount: £{invoice['total_amount']}")
print(f"  Date: {invoice['invoice_date']}")

# Step 4: Run Matching
print("\n[4/4] Running Invoice-to-Transaction Matching...")
resp = requests.post(f"http://127.0.0.1:8000/invoice/match?session_id={session_id}")

if resp.status_code != 200:
    print(f"❌ FAILED: {resp.status_code}")
    print(resp.json())
    exit(1)

data = resp.json()
matches = data['matches']
print(f"✓ SUCCESS: {len(matches)} match(es) found\n")

for m in matches:
    print(f"Invoice: {m['invoice']['supplier_name']}")
    print(f"  Amount: £{m['invoice']['total_amount']}, Date: {m['invoice']['invoice_date']}")
    print(f"  Match Score: {m['confidence']} ({m['classification']})")
    print(f"  Explanation: {m['explanation']}")
    
    if m['transaction']:
        txn = m['transaction']
        print(f"  ✓ MATCHED TRANSACTION:")
        print(f"    - Date: {txn['date']}")
        print(f"    - Description: {txn['description']}")
        print(f"    - Amount: £{abs(txn['amount'])}")
        if m['confidence'] >= 80:
            print(f"\n  🎉 HIGH CONFIDENCE MATCH!")
        elif m['confidence'] >= 50:
            print(f"\n  ⚠️ MEDIUM CONFIDENCE - Review before confirming")
    else:
        print(f"  ❌ NO MATCH FOUND")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
