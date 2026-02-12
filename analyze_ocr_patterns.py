#!/usr/bin/env python
"""Analyze OCR corruption patterns in FNB PDF 20260119115115880"""

ocr_samples = [
    '120 Oct |FNB App Transfer From Transfer 4162.00Cr 1,038.69Cr',
    '120 Oct |#Dedit Card Intl POS Unsuccess #Fee Declined Foreign Tr 400974501 71499855, 8.00 1,030.65Cr',
    '120 Oct |FNB App Prepaid Airtime 0629817671 25.00 1,005.69Cr| 1.60)',
    '24 Oct |FNB App Transfer From Transfer 100.008Gr; 1,105.69Cr;',
    '21 Oct |POS Purchase Checkers Sixty60 412752°6823 18 Oct 247.92 857.77Gr',
    '24 Oct |POS Purchase 10.00 Github, Inc. 412752°6823 18 Oct 179.40 676.37Cr',
    '122 Oct [POS Purchase Checkers Sity60 412762°6823 19 Oct 278.97 399.40Gr;',
    '22 Oct |Fuet Purchase Ae Griffiths 412752*6823 19 Oct 150.00 249.40Cr',
    '23 Oct |#Service Fees int Pymt Fee-34.99 Googl 0.87 248.53Cr]',
    '23 Oct |FNB App Transfer From Transfer 1,600.00Cr| 1,848.53Cr]',
    '23 Oct |Payshap Account Off-Us Chris 1,000.00 848.53Cr]',
    '23 Oct |FNS App Prepaid Airtime 0629817671 25.00 823.53Cr| 1.60)',
    '123 Oct |Payshap Account Off Us Chris 700.00 123,.53Cr]',
    '31 Oct |Rm Miwaycolle0G00008803 197.86 3,819.43Cr}',
    '31 Oct |DebiCheck Budget Ins778803907P 2,567.05 1,252.38Cr]',
    '31 Oct |Magtape Debit Mviainsuremymspt-0350331251031 438,91 813.47Cr',
    '101 Nov |FNB App Transfer From Transfer 4,000.00Cr] 4,484.49Cr}',
    '1 Nov |Flectricity Prepaid Electricity 04297814248 4,000.00 3,484.49Cr} 3.30)',
    '(03 Nov |POS Purchase Ksa979 KFC Nonesi M 412752°6823 34 Oct 256.42 3,198.07Cr',
]

print("="*80)
print("OCR CORRUPTION PATTERNS ANALYSIS")
print("="*80)

print("\n1. DATE ISSUES:")
print("-" * 80)
print("  a) Leading digits instead of day: '120 Oct', '122 Oct', '123 Oct', '101 Nov', '104 Nov', etc.")
print("     → Likely OCR reading '1' at start of line as part of date")
print("     → Fix: Remove leading '1' if date becomes invalid")
print("  b) Month typos: '0ct' instead of 'Oct'")
print("     → Pattern: Zero (0) instead of letter O")
print("     → Fix: Replace '0ct', '0ct', etc. with proper month names")

print("\n2. CURRENCY/AMOUNT ISSUES:")
print("-" * 80)
print("  a) Wrong currency suffixes: 'Gr' instead of 'Cr', 'Gr;' instead of 'Cr'")
print("     → Pattern: 'G' instead of 'C'")
print("     → Fix: Normalize Gr/Gr; to Cr")
print("  b) Bad separators: '100.008Gr;' should be '100.00' with 'Cr'")
print("     → Pattern: 8 instead of 0, comma instead of period")
print("     → Fix: Clean up amount format before processing")
print("  c) Balance corruption: '123,.53Cr]' (comma in wrong place)")
print("     → Fix: Normalize number formatting")

print("\n3. DESCRIPTION ISSUES:")
print("-" * 80)
print("  a) OCR character mistakes:")
print("     → 'Flectricity' (should be 'Electricity')")
print("     → 'Debit' spelled 'Dedit'")
print("     → 'Fuet' instead of 'Fuel'")
print("     → 'Colle0G' (zero G should be letters)")
print("  b) Special character corruptions:")
print("     → '°' (degree symbol) instead of '°' (proper formatting)")
print("     → '§' (section sign) instead of '3'")
print("     → '*' instead of other punctuation")
print("  c) Garbage symbols: '[', ']', '}', ')', '|' at end of lines")
print("     → Fix: Strip trailing garbage characters")

print("\n4. FIELD SEPARATOR ISSUES:")
print("-" * 80)
print("  a) Multiple field delimiters: '|', '[', ']', '}'")
print("  b) Lines may have: Date | Desc | Desc(continued) | Amount | Balance | Bank Charge")
print("  c) Some lines have nested descriptions with dates")

print("\n5. POSSIBLE SOLUTIONS:")
print("-" * 80)
print("  1. Pre-process OCR text to fix common patterns:")
print("     - Replace 'Gr[;|}]' with 'Cr'")
print("     - Replace '0ct' with 'Oct'")
print("     - Remove leading '1' from dates like '120 Oct' → '20 Oct'")
print("     - Strip garbage symbols from line ends")
print("  2. Improve date parsing to handle typos")
print("  3. Improve amount extraction to handle corrupted formats")
print("  4. Use more lenient description parsing")
