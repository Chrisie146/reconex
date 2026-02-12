import pdfplumber

def analyze_pdf(filename):
    print(f"\n{'='*80}")
    print(f"ANALYZING: {filename}")
    print('='*80)
    
    with pdfplumber.open(filename) as pdf:
        print(f"Total pages: {len(pdf.pages)}\n")
        
        # Get first 2 pages
        for page_num in range(min(2, len(pdf.pages))):
            page = pdf.pages[page_num]
            print(f"\n--- PAGE {page_num + 1} ---")
            
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                print(f"Total lines: {len(lines)}")
                print("\nFirst 25 lines:")
                for i, line in enumerate(lines[:25]):
                    print(f"{i+1:2d}: {line}")
            else:
                print("  [No text extracted - likely image/scanned PDF]")

analyze_pdf('Standard bank.pdf')
analyze_pdf('Absa.pdf')
