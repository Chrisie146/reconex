# Standard Bank Parser Fix - Summary

## Issue
When uploading Standard Bank statements, all transactions were showing as expenses (negative amounts). Income transactions (credits) were not being detected or parsed correctly.

## Root Cause
The `_parse_standard_bank_business_text` function in [pdf_parser.py](backend/services/pdf_parser.py) had two issues:

1. **Date Format Mismatch**: The parser expected MMDD format (4 digits) but the actual PDF had YYYYMMDD format (8 digits). This caused the main parsing logic to fail and fall back to a less sophisticated parser.

2. **Fallback Logic Bug**: The fallback logic didn't properly handle:
   - YYYYMMDD dates being mixed into the amounts array
   - Large balance values being treated as transaction amounts
   - Proper selection between three amount columns (Service_Fee, Debit, Credit)

When processing credit (income) transactions like:
```
10 ELECTRONIC BANKING PAYMENT FR 0.00 0.00 11,178.00 20240226 6,168,730.27
```

The fallback parser would extract all numeric values including the date and balance:
```
[0.0, 0.0, 11178.0, 20240226.0, 6168730.27]
```

Then use `min(amounts) = 0.0`, causing the transaction to be skipped.

## Solution Applied

### 1. Fixed Fallback Logic (Lines 1406-1446)
- Added filtering to **exclude YYYYMMDD dates** (8-digit numbers)
- Added filtering to **exclude large balance amounts** (> 10 million)
- Improved amount selection logic to properly handle:
  - **Debits (expenses)**: Use negative amounts
  - **Credits (income)**: Use positive amounts (excluding service fees)

### 2. Fixed MMDD Date Logic (Lines 1501-1538)
- Added YYYYMMDD date exclusion
- Improved credit/debit selection to use last non-zero value
- Properly handles the three-column format: Service_Fee, Debit, Credit

## Code Changes

**File**: [backend/services/pdf_parser.py](backend/services/pdf_parser.py)

### Change 1: Fallback Parser (Lines 1406-1446)
```python
# Skip YYYYMMDD dates (8 digits)
if len(clean_token) == 8 and clean_token.isdigit():
    continue

# Skip very large values (likely balance, not transaction)
if abs(val) > 10000000:  # 10 million threshold
    continue

# Standard Bank format: Service_Fee, Debit (negative), Credit (positive)
negatives = [amt for amt in amounts if amt < 0]
positives = [amt for amt in amounts if amt > 0]

if negatives:
    # Has debit (expense) - use the negative amount
    amount = max(negatives)  # Closest to zero = actual transaction
elif positives:
    # Has credit (income) - use smallest positive (not the balance)
    amount = min(positives)
else:
    amount = 0.0
```

### Change 2: MMDD Date Parser (Lines 1501-1538)
```python
# Skip YYYYMMDD dates (8 digits)
if len(clean_token) == 8 and clean_token.isdigit():
    continue

# Determine transaction amount
negatives = [amt for amt in amounts if amt < 0]
positives = [amt for amt in amounts if amt > 0]

if negatives:
    # Has debit (expense) - use the last/largest magnitude negative
    amount = negatives[-1] if len(negatives) > 1 else negatives[0]
elif positives:
    # Has credit (income) - use the last/largest positive (skip service fee)
    amount = positives[-1] if len(positives) > 1 else positives[0]
else:
    # All zeros - skip this transaction
    amount = 0.0
```

## Test Results

### Before Fix
```
Total transactions: 119
Expenses (negative): 119  ❌
Income (positive): 0      ❌
Net total: R (large negative)
```

### After Fix
```
Total transactions: 233
Expenses (negative): 119  ✅
Income (positive): 114    ✅
Net total: R 996,648.65   ✅
```

### Sample Income Transactions
```
Date       Description                        Amount
2025-01-01 10 ELECTRONIC BANKING PAYMENT FR   11,178.00
2025-01-01 10 ELECTRONIC BANKING PAYMENT FR   545,082.08
2025-01-01 10 ELECTRONIC BANKING TRANSFER FR  200,000.00
2025-01-01 11 ELECTRONIC BANKING PAYMENT FR   721,690.12
```

### Sample Expense Transactions
```
Date       Description                        Amount
2025-01-01 10 ELECTRONIC BANKING TRANSFER TO  -92.71
2025-01-01 10 ELECTRONIC BANKING PAYMENT TO   -13,026.61
2025-01-01 10 ELECTRONIC BANKING PAYMENT TO   -366,227.78
```

## Verification

✅ **Standard Bank**: Fixed - now shows both income and expenses  
✅ **ABSA**: Unaffected - still works correctly  
✅ **Capitec**: Unaffected - still works correctly  
✅ **API Workflow**: End-to-end upload works correctly

## Impact

- **No breaking changes** to other bank parsers
- **Backward compatible** with existing Standard Bank formats
- **Handles multiple Standard Bank formats**:
  - YYYYMMDD date format (fixed)
  - MMDD date format (already working)
  - OCR-extracted format (already working)

## Files Modified

- [backend/services/pdf_parser.py](backend/services/pdf_parser.py)

## Files Added for Testing

- [test_sb_fix.py](test_sb_fix.py) - Comprehensive Standard Bank parser test
- [test_api_workflow.py](test_api_workflow.py) - End-to-end API upload simulation
- [verify_other_banks.py](verify_other_banks.py) - Regression testing for other banks
- [debug_sb_format.py](debug_sb_format.py) - Format detection debugging
- [debug_sb_both_lines.py](debug_sb_both_lines.py) - Income/expense parsing debugging

---

**Status**: ✅ **FIXED AND TESTED**  
**Date**: 2026-02-11  
**Tested With**: Bank_statements/Standard bank.pdf
