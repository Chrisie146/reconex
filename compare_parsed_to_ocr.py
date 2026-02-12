from pdf2image import convert_from_path
import pytesseract
import sys
sys.path.insert(0, 'backend')
from services.pdf_parser import _parse_fnb_ocr_text

PDF='FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'
images = convert_from_path(PDF, dpi=200)
ocr_text = '\n'.join(pytesseract.image_to_string(img, lang='eng') for img in images)
parsed = _parse_fnb_ocr_text(ocr_text)

import re
amount_pattern = re.compile(r'\b(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})')

discrepancies = []

ocr_lines = ocr_text.split('\n')
for pr in parsed:
    date, desc, amt_str = pr
    amt_val = float(amt_str.replace('C',''))
    # find OCR lines containing the description snippet
    found = False
    for line in ocr_lines:
        if desc.split()[0][:6] in line or desc[:10] in line:
            # get first amount in line
            ams = amount_pattern.findall(line)
            if not ams:
                continue
            first_amt = float(ams[0].replace(',','').replace(' ','').strip())
            if abs(first_amt - amt_val) > 0.01:
                discrepancies.append((date, desc, amt_val, first_amt, line))
            found = True
            break
    if not found:
        discrepancies.append((date, desc, amt_val, None, 'NO OCR LINE MATCH'))

print('Discrepancies count:', len(discrepancies))
for d in discrepancies:
    print(d)
