# FNB CSV Income/Expense Fix - Summary

## Problem
FNB CSV files (direct bank exports) were treating income as expenses. In the file `62514285346.csv`, positive amounts like `22` and `1043` were being incorrectly parsed as negative (expenses) instead of positive (income).

## Root Cause
The FNB parser had logic that assumed unsigned amounts (amounts without a minus sign) should be treated as expenses (negative). This assumption was valid for OCR-parsed CSV files where amounts don't have signs, but not for direct CSV exports where amounts already have explicit +/- signs.

## Solution
Implemented format detection to distinguish between three FNB CSV formats:

1. **CSV Format** (Direct Bank Export)
   - Amounts have explicit signs: `-2.75` (expense), `22` (income)
   - Positive = Income, Negative = Expense
   - Uses new `parse_amount_csv()` method

2. **OCR Format** (Scanned PDF)
   - Unsigned amounts with C/K suffix: `22.00C` (income), `2.75` (expense)
   - Suffix C/K = Income, No suffix = Expense
   - Uses new `parse_amount_ocr()` method

3. **Table Format** (Separate debit/credit columns)
   - Already handled correctly

## Files Modified
- `backend/services/bank_adapters.py`
  - Updated `FNBAdapter._detect_format()` to identify format type
  - Added `FNBAdapter._normalize_csv_format()` for CSV format
  - Updated `FNBAdapter._normalize_scanned_format()` to use OCR parser
  - Added `FNBAdapter.parse_amount_csv()` static method
  - Added `FNBAdapter.parse_amount_ocr()` static method
  - Improved `FNBAdapter.parse_amount_signed()` documentation

## Test Results
✓ CSV Format (62514285346.csv)
  - Detected as: csv
  - Total Income: R 165,734.53
  - Total Expenses: R 163,686.17
  - Net: R 2,048.36

✓ OCR Format (C suffix)
  - Detected as: ocr
  - Correctly parses unsigned amounts as negative
  - Correctly parses C-suffix amounts as positive

✓ Other Parsers
  - ABSA adapter: Not affected
  - Standard Bank adapter: Not affected

## Backwards Compatibility
- All existing functionality is preserved
- Other bank parsers continue to work unchanged
- No data is lost or corrupted
