"""Check OCR lines around 1212 date and 29504 amount."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path('.') / 'backend'))
from services.pdf_parser import convert_from_bytes, pytesseract

pdf_path = 'xxxxx0819_31.12.25.pdf'

with open(pdf_path, 'rb') as f:
    data = f.read()

images = convert_from_bytes(data, dpi=200)
for pg, img in enumerate(images, start=1):
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    for i, line in enumerate(text.splitlines(), start=1):
        # Look for lines with 1212 date or 29504/29400 amounts
        if '1212' in line or '29504' in line or '29400' in line:
            # Print context
            lines_list = text.splitlines()
            start = max(0, i-3)
            end = min(len(lines_list), i+3)
            print(f"\n--- Page {pg}, Line {i} ---")
            for j in range(start, end):
                marker = '>>' if j == i-1 else '  '
                print(f"{marker} {lines_list[j]}")
