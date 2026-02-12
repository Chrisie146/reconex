#!/usr/bin/env python
from services.matcher import score_match

# Test with the improved matcher
print("=== Testing Improved Matcher ===\n")

# Invoice with customer name included
invoice = {
    "id": 18,
    "supplier_name": "Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON",
    "invoice_date": "2026-01-01",
    "invoice_number": "3935659",
    "total_amount": 849.0,
    "vat_amount": 110.74
}

# Bank transaction
txn = {
    "id": 999,
    "date": "2026-01-01",
    "description": "Herotel",
    "amount": 849.0
}

result = score_match(invoice, txn)
print(f"Invoice: {invoice['supplier_name']}, Amount: £{invoice['total_amount']}, Date: {invoice['invoice_date']}")
print(f"Txn: {txn['description']}, Amount: £{txn['amount']}, Date: {txn['date']}")
print(f"\nScore: {result['score']} ({result['classification']})")
print(f"Matched: {result['matched']}")
print(f"Explanation: {result['explanation']}")

print("\n" + "="*50)
print("Expected: Score=100, Classification=High (all three criteria match)")
print(f"Got:      Score={result['score']}, Classification={result['classification']}")

if result['score'] == 100 and result['classification'] == 'High':
    print("\n✓ MATCHER FIXED - All criteria now match correctly!")
else:
    print("\n✗ MATCHER ISSUE - Criteria not matching as expected")
