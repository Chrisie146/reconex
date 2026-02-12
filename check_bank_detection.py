"""Check what bank is detected for the PDF."""

import sys
import io
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

try:
    from pdf2image import convert_from_bytes
    import pytesseract
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

pdf_path = 'xxxxx0819_31.12.25.pdf'

with open(pdf_path, 'rb') as f:
    file_content = f.read()

# Convert to images and OCR (like pdf_to_csv_bytes does)
images = convert_from_bytes(file_content, dpi=200)
ocr_texts = []
for idx, img in enumerate(images[:3], start=1):  # Just first 3 pages
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    if text:
        ocr_texts.append(text)
        print(f"Page {idx}: {len(text)} chars")

full_ocr_text = '\n'.join(ocr_texts).lower()

# Check bank detection
print("\nBank detection:")
print(f"  'standard bank' in text: {'standard bank' in full_ocr_text}")
print(f"  'sbsa' in text: {'sbsa' in full_ocr_text}")
print(f"  'absa' in text: {'absa' in full_ocr_text}")
print(f"  'fnb' in text: {'fnb' in full_ocr_text}")
print(f"  'capitec' in text: {'capitec' in full_ocr_text}")

# Find which one matches
if 'standard bank' in full_ocr_text or 'sbsa' in full_ocr_text:
    detected_bank = 'standard_bank'
elif 'absa' in full_ocr_text or 'absacapital' in full_ocr_text:
    detected_bank = 'absa'
elif 'fnb' in full_ocr_text or 'first national' in full_ocr_text:
    detected_bank = 'fnb'
elif 'capitec' in full_ocr_text:
    detected_bank = 'capitec'
else:
    detected_bank = 'capitec'  # default

print(f"\nDetected bank: {detected_bank}")
