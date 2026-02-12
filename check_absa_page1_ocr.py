import pytesseract
from pdf2image import convert_from_path

pdf_path = r'C:\Users\christopherm\statementbur_python\Absa.pdf'

# OCR page 1 to see Amount sections
images = convert_from_path(pdf_path, dpi=200)
if len(images) > 0:
    img = images[0].convert('L')
    text = pytesseract.image_to_string(img, lang='eng')
    print("=== OCR Text from Page 1 ===")
    print(text)
    
    print("\n\n=== Search for amounts around 3175 or 1430 ===")
    for line in text.split('\n'):
        if any(x in line for x in ['3175', '1430', '819', '819 20 21 22']):
            print(line)
