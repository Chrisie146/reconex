import sys
sys.path.insert(0, r'c:\Users\christopherm\statementbur_python\backend')

import pdfplumber
from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\christopherm\statementbur_python\xxxxx0819_31.12.25.pdf"

print(f"Analyzing PDF with OCR: {pdf_path}")
print("="*60)

# Try OCR on first few pages
images = convert_from_path(pdf_path, first_page=1, last_page=3)

for i, image in enumerate(images):
    print(f"\nPage {i+1} - OCR Text:")
    text = pytesseract.image_to_string(image)
    print(text[:1500])
    print("="*60)
