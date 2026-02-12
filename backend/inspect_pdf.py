import sys
sys.path.insert(0, '.')
import pdfplumber

with pdfplumber.open('../FNB_PREMIER_CURRENT_ACCOUNT_170.pdf') as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print("\n=== PAGE 1 CONTENT ===")
    page = pdf.pages[0]
    text = page.extract_text()
    print("Text preview (first 1500 chars):")
    print(text[:1500])
    print("\n=== PAGE 1 TABLES ===")
    tables = page.extract_tables()
    if tables:
        for i, table in enumerate(tables):
            print(f"\nTable {i}:")
            print(f"  Rows: {len(table)}, Cols: {len(table[0]) if table else 0}")
            # Show first 5 rows
            for row_idx, row in enumerate(table[:5]):
                print(f"  Row {row_idx}: {[str(c)[:30] + '...' if len(str(c)) > 30 else str(c) for c in row]}")
