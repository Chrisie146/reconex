"""Export the current Standard Bank parsing to CSV for debugging."""

import sys
import csv
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from services.pdf_parser import pdf_to_csv_bytes

# Parse the Standard Bank PDF
pdf_path = 'xxxxx0819_31.12.25.pdf'

print(f"Parsing {pdf_path}...")
try:
    with open(pdf_path, 'rb') as f:
        file_content = f.read()
    
    csv_bytes, _, _ = pdf_to_csv_bytes(file_content)
    
    # Save to file
    with open('debug_out_standard_bank.csv', 'wb') as f:
        f.write(csv_bytes)
    
    print(f"✓ Saved to debug_out_standard_bank.csv")
    
    # Show summary
    csv_text = csv_bytes.decode('utf-8')
    lines = csv_text.split('\n')
    print(f"✓ Total lines: {len(lines)}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
