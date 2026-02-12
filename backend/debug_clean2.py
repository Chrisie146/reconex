#!/usr/bin/env python
import re

s = "Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON"
s_lower = s.lower()

company_suffix_pattern = r'(\b(?:pty|ltd|limited|llc|inc|corp|company|co|llp|gmbh|sa|ag|ab|bv|nv|cv|as)\b)'
matches = list(re.finditer(company_suffix_pattern, s_lower))

print(f"Original: {s}")
print(f"Lowercase: {s_lower}")
print(f"Matches found: {len(matches)}")
for i, m in enumerate(matches):
    print(f"  {i}: '{m.group()}' at pos {m.start()}-{m.end()}")

if matches:
    last_match = matches[-1]
    print(f"\nLast match: '{last_match.group()}' at {last_match.start()}-{last_match.end()}")
    
    before_suffix = s_lower[:last_match.start()]
    print(f"Before suffix: '{before_suffix}'")
    
    words_before = before_suffix.split()
    print(f"Words before: {words_before}")
    
    if words_before:
        last_word = words_before[-1]
        print(f"Last word: '{last_word}'")
        company_start = before_suffix.rfind(last_word)
        print(f"Company start: {company_start}")
        company_name = s[company_start:last_match.end()]
        print(f"Company name: '{company_name}'")
