from services.invoice_parser import extract_invoice_metadata, _extract_text
import sys
p='uploads/02cc367bc079468e9894f82389cd7d94_Invoice_23607174.pdf'
with open(p,'rb') as f:
    b=f.read()
res = _extract_text(b)
if isinstance(res, tuple):
    lines, method = res
else:
    lines = res
    method = 'unknown'
meta = extract_invoice_metadata(b)
print('file:',p)
print('extraction_method:', method)
print('lines_count:', len(lines))
print('first_lines:')
for i,l in enumerate(lines[:40],1):
    print(i,':',l)
print('\nmeta:')
print(meta)
