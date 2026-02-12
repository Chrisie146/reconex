import pdfplumber
import sys

pdf_path = r'c:\Users\christopherm\statementbur_python\FNB_ASPIRE_CURRENT_ACCOUNT_132-1.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")
    
    for page_num, page in enumerate(pdf.pages):
        print(f"\n{'='*60}")
        print(f"PAGE {page_num}")
        print('='*60)
        
        # Extract tables
        tables = page.extract_tables()
        print(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            print(f"\n--- Table {i} (rows: {len(table)}) ---")
            if i == 2:  # The transaction table
                print("This appears to be the transaction table!")
                print(f"Header: {table[0]}")
                print(f"\nFirst 20 data rows:")
                for row_idx, row in enumerate(table[1:21]):
                    print(f"Row {row_idx+1}: {row}")
                
                # Try to parse it
                print("\n\n=== ATTEMPTING TO PARSE ===")
                # Get amounts from column 2
                if len(table) > 1 and len(table[1]) > 2:
                    amounts_col = table[1][2]
                    balances_col = table[1][4] if len(table[1]) > 4 else None
                    print(f"Amounts column (split by newline):")
                    if amounts_col:
                        for idx, amt in enumerate(amounts_col.split('\n')[:20]):
                            print(f"  {idx}: {amt}")
                    print(f"\nBalances column (split by newline):")
                    if balances_col:
                        for idx, bal in enumerate(balances_col.split('\n')[:20]):
                            print(f"  {idx}: {bal}")
