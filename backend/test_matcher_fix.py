#!/usr/bin/env python
from services.matcher import _clean_supplier, _fuzzy_ratio

print('Test 1 - Invoice supplier:')
inp = 'Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON'
out = _clean_supplier(inp)
print('  Input:', repr(inp))
print('  Output:', repr(out))
print()

print('Test 2 - Bank description:')
inp = 'Herotel'
out = _clean_supplier(inp)
print('  Input:', repr(inp))
print('  Output:', repr(out))
print()

print('Test 3 - Fuzzy match test:')
s1 = _clean_supplier('Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON')
s2 = _clean_supplier('Herotel')
ratio = _fuzzy_ratio(s1, s2)
print(f'  Ratio between "{s1}" and "{s2}":', ratio)
print()

print('Test 4 - Full score match test:')
from services.matcher import score_match
invoice = {
    "id": 18,
    "supplier_name": "Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON",
    "invoice_date": "2026-01-01",
    "total_amount": 849.0
}
txn = {
    "id": 123,
    "date": "2026-01-01",
    "description": "Herotel",
    "amount": 849.0
}
result = score_match(invoice, txn)
print(f'  Score: {result["score"]} ({result["classification"]})')
print(f'  Explanation: {result["explanation"]}')
