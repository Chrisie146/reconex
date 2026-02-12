import pdfplumber

pdf_path = r'C:\Users\christopherm\statementbur_python\Absa.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    for i, page in enumerate(pdf.pages[:3]):  # Check first 3 pages
        print(f"\n=== Page {i+1} ===")
        text = page.extract_text()
        if text:
            text_lower = text.lower()
            print(f"Length: {len(text)} chars")
            print(f"Contains 'absa': {'absa' in text_lower}")
            print(f"Contains 'capitec': {'capitec' in text_lower}")
            print(f"Contains 'fnb': {'fnb' in text_lower}")
            print(f"Contains 'standard bank': {'standard bank' in text_lower}")
            print("\nFirst 500 chars:")
            print(text[:500])
        else:
            print("(No text extracted)")
