import sys
sys.path.insert(0, r'c:\Users\christopherm\statementbur_python\backend')

import pdfplumber

pdf_path = r"c:\Users\christopherm\statementbur_python\xxxxx0819_31.12.25.pdf"

print(f"Analyzing PDF: {pdf_path}")
print("="*60)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Number of pages: {len(pdf.pages)}")
    
    # Check first page
    page = pdf.pages[0]
    print(f"\nPage 1 - Extracting text:")
    text = page.extract_text()
    print(text[:2000] if text else "No text extracted")
    
    print("\n" + "="*60)
    print("Page 1 - Extracting tables:")
    tables = page.extract_tables()
    print(f"Number of tables found: {len(tables)}")
    
    if tables:
        for i, table in enumerate(tables[:2]):  # Show first 2 tables
            print(f"\nTable {i+1}:")
            print(f"Rows: {len(table)}")
            if len(table) > 0:
                print(f"Header: {table[0]}")
                print(f"First few rows:")
                for row in table[1:6]:
                    print(f"  {row}")
