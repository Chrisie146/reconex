#!/usr/bin/env python
import re

STOP_WORDS = {"pty", "ltd", "payment", "eft", "ppd", "pvt", "ptyltd", "limited"}

s = "Herotel (Pty) Ltd CHRISTOPHER WILLIAM MCPHERSON"
original = s.strip()
s_lower = original.lower()

company_suffix_pattern = r'(\b(?:pty|ltd|limited|llc|inc|corp|company|co|llp|gmbh|sa|ag|ab|bv|nv|cv|as)\b)'

matches = list(re.finditer(company_suffix_pattern, s_lower))
print(f"Matches: {len(matches)}")

if matches:
    first_match = matches[0]
    before_suffix = s_lower[:first_match.start()]
    words = before_suffix.split()
    print(f"Before suffix: '{before_suffix}'")
    print(f"Words: {words}")
    
    if words:
        company_word = words[-1]
        print(f"Company word: '{company_word}'")
        company_start = original.lower().find(company_word)
        print(f"Company start: {company_start}")
        last_match = matches[-1]
        company_name = original[company_start:last_match.end()]
        print(f"Company name: '{company_name}'")
        
        # Clean it
        company_clean = company_name.lower()
        print(f"Lowercase: '{company_clean}'")
        
        company_clean = re.sub(r"[^a-z0-9\s]", " ", company_clean)
        print(f"After removing punct: '{company_clean}'")
        
        parts = [p.strip() for p in company_clean.split() if p.strip()]
        print(f"Parts: {parts}")
        
        parts = [p for p in parts if p not in STOP_WORDS and len(p) > 0]
        print(f"After filtering: {parts}")
        
        result = " ".join(parts)
        print(f"Result: '{result}'")
