#!/usr/bin/env python
from services.matcher import _clean_supplier, _fuzzy_ratio

invoice_supplier = "Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON"
txn_description = "FNB App Payment To Herotel (Pty) Ltd Lcchr052 849.00"

inv_clean = _clean_supplier(invoice_supplier)
txn_clean = _clean_supplier(txn_description)

print(f"Invoice supplier: {invoice_supplier}")
print(f"  Cleaned: '{inv_clean}'")
print()
print(f"Txn description: {txn_description}")
print(f"  Cleaned: '{txn_clean}'")
print()

ratio = _fuzzy_ratio(inv_clean, txn_clean)
print(f"Fuzzy ratio: {ratio}")
print(f"Match: {ratio >= 0.70}")
