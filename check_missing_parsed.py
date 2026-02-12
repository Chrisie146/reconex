from pdf2image import convert_from_path
import pytesseract
import sys
sys.path.insert(0, 'backend')
from services.pdf_parser import _parse_fnb_ocr_text

PDF='FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'

images = convert_from_path(PDF, dpi=200)
ocr_text = '\n'.join(pytesseract.image_to_string(img, lang='eng') for img in images)

keywords = ['Service Fees', 'FNB App Prepaid', 'POS Purchase Superspar', 'Payments Bundle Fee']

parsed_rows = _parse_fnb_ocr_text(ocr_text)
parsed_summaries = set((r[0], r[1][:30], float(r[2].replace('C','')) if 'C' in r[2] else float(r[2])) for r in parsed_rows)

print('=== Parsed rows count:', len(parsed_rows), '===\n')

for i, line in enumerate(ocr_text.split('\n')):
    if any(k in line for k in keywords):
        print('OCR Line:', line)
        # print neighbors
        lines = ocr_text.split('\n')
        start = max(0, i-2)
        end = min(len(lines), i+3)
        print('  Context:')
        for j in range(start, end):
            print(f'    {j}: {lines[j]}')
        # find amounts
        import re
        amount_pattern = re.compile(r'\b(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})')
        amounts = amount_pattern.findall(line)
        print('  amounts found in OCR:', amounts)
        # Try to match parsed row by amount and keyword in description
        matched = False
        for pr in parsed_rows:
            pr_amt = float(pr[2].replace('C','')) if 'C' in pr[2] else float(pr[2])
            for a in amounts:
                try:
                    a_clean = float(a.replace(',','').replace(' ','').strip())
                except:
                    continue
                if abs(pr_amt - a_clean) < 0.01 and any(k.lower() in pr[1].lower() for k in keywords):
                    matched = True
                    print('  -> Matched parsed row:', pr)
                    break
            if matched:
                break
        if not matched:
            print('  -> NOT FOUND in parsed rows')
        print()