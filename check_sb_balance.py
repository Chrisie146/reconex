import sys
sys.path.insert(0, r'c:\Users\christopherm\statementbur_python\backend')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\christopherm\statementbur_python\xxxxx0819_31.12.25.pdf"

print("Extracting first and last page OCR for balance information...")

# Get first page
images = convert_from_path(pdf_path, first_page=1, last_page=1)
text1 = pytesseract.image_to_string(images[0])

print("First page:")
print(text1[:1500])

print("\n" + "="*60)

# Get last page
images = convert_from_path(pdf_path, first_page=18, last_page=18)
text18 = pytesseract.image_to_string(images[0])

print("Last page (18):")
print(text18[:1500])

# Look for balance information
print("\n" + "="*60)
print("Balance information:")

# From first page
balance_match = re.search(r'BALANCE BROUGHT FORWARD[:\s]+([R\d,.-]+)', text1, re.IGNORECASE)
if balance_match:
    print(f"Opening balance: {balance_match.group(1)}")

# Look for month-end balance
month_end = re.search(r'Month-end Balance\s+([R\d,.-]+)', text1, re.IGNORECASE)
if month_end:
    print(f"Month-end balance: {month_end.group(1)}")
