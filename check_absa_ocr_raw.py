import pdfplumber
import pytesseract
from pdf2image import convert_from_path

pdf_path = r'C:\Users\christopherm\statementbur_python\Absa.pdf'

# OCR page 2 to see raw text
images = convert_from_path(pdf_path, dpi=200)
if len(images) > 1:
    img = images[1].convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    print("=== OCR Text from Page 2 (first 2000 chars) ===")
    print(text[:2000])
    print("\n\n=== Lines with large amounts (1000+) ===")
    for line in text.split('\n'):
        if any(x in line for x in ['4464', '822', '4230', '1114', '2280', '2250', '3125', '2271', '1430', '300000']):
            print(line)
