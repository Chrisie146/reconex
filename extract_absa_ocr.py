"""
Extract and save OCR text from ABSA PDF for inspection
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.ocr import ocr_pdf_bytes

with open('Absa.pdf', 'rb') as f:
    pdf_content = f.read()

ocr_text = ocr_pdf_bytes(pdf_content, dpi=400)

# Save to file for inspection
with open('absa_ocr_output.txt', 'w', encoding='utf-8') as f:
    f.write(ocr_text)

print(f"OCR text saved to absa_ocr_output.txt ({len(ocr_text)} chars)")
print("\nFirst 2000 chars:")
print(ocr_text[:2000])
