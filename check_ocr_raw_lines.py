from pdf2image import convert_from_path
import pytesseract
import re

# Convert PDF to image and extract OCR text
images = convert_from_path('FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf', dpi=200)
page1_text = pytesseract.image_to_string(images[0])

print("=== Looking for lines with Service Fees, FNB App Prepaid, POS Purchase ===\n")
for line in page1_text.split('\n'):
    if any(keyword in line for keyword in ['Service Fees', 'FNB App Prepaid', 'POS Purchase']):
        print(f"Line: {line}")
        
        # Extract all amounts from this line
        amount_pattern = r'\b(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})'
        amounts = re.findall(amount_pattern, line)
        if amounts:
            print(f"  All amounts found: {amounts}")
        print()
