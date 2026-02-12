#!/usr/bin/env python
import re

s = "herotel (pty) ltd christopher william mcpherson"
company_pattern = r'([a-z0-9\s]+?(?:ltd|pty|pvt|limited|llc|inc|corp|company|co|llp|gmbh|sa|ag|ab|bv|nv|cv|as)\b)'
match = re.search(company_pattern, s)
print(f"Pattern: {company_pattern}")
print(f"Input: {s}")
print(f"Match: {match}")
if match:
    print(f"Matched: {match.group(1)}")
else:
    print("No match")

# Try a simpler approach
print("\n--- Simpler approach ---")
# Split on all-uppercase names (like CHRISTOPHER WILLIAM MCPHERSON)
s2 = "herotel (pty) ltd CHRISTOPHER WILLIAM MCPHERSON"
# Find the last lowercase word sequence before uppercase
parts = s2.split()
print(f"Parts: {parts}")
company_parts = []
for p in parts:
    if p[0].isupper() and len(company_parts) > 0:
        break
    company_parts.append(p)
print(f"Company parts: {company_parts}")
print(f"Company: {' '.join(company_parts)}")
