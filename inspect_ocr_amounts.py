"""Inspect OCR text around flagged large amounts to determine if they're balance/summary lines."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / 'backend'))
from services.pdf_parser import convert_from_bytes, pytesseract

pdf_path = 'xxxxx0819_31.12.25.pdf'
amt_strings = ['372423.59', '372,423.59', '240157.00', '240,157.00', '635027.18', '635,027.18', '332925.71', '332,925.71']

with open(pdf_path, 'rb') as f:
    data = f.read()

images = convert_from_bytes(data, dpi=200)
ocr_lines = []
for pg, img in enumerate(images, start=1):
    img = img.convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    for i, line in enumerate(text.splitlines(), start=1):
        ocr_lines.append((pg, i, line))

full_text = '\n'.join(f"[P{pg}:L{ln}] {line}" for pg, ln, line in ocr_lines)

found = False
for s in amt_strings:
    if s in full_text:
        found = True
        print(f"\n--- Matches for '{s}' ---")
        for idx, (pg, ln, line) in enumerate(ocr_lines):
            if s in line:
                start = max(0, idx-3)
                end = min(len(ocr_lines), idx+4)
                for j in range(start, end):
                    pg2, ln2, l2 = ocr_lines[j]
                    marker = '>>' if j == idx else '  '
                    print(f"{marker} [P{pg2}:L{ln2}] {l2}")

if not found:
    print("No exact matches found for flagged amounts. Searching normalized numbers...")
    # Try matching without punctuation
    def normalize(s):
        return ''.join(c for c in s if c.isdigit())
    norm_map = {normalize(s): s for s in amt_strings}
    for idx, (pg, ln, line) in enumerate(ocr_lines):
        nline = normalize(line)
        for nn, orig in norm_map.items():
            if nn and nn in nline:
                print(f"\n--- Approx match for '{orig}' in OCR ---")
                start = max(0, idx-3)
                end = min(len(ocr_lines), idx+4)
                for j in range(start, end):
                    pg2, ln2, l2 = ocr_lines[j]
                    marker = '>>' if j == idx else '  '
                    print(f"{marker} [P{pg2}:L{ln2}] {l2}")

print('\nDone.')
