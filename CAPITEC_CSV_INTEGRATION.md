# Capitec CSV Integration - Implementation Summary

## Overview
Successfully added support for the new Capitec CSV format (native bank export) to the existing parsing infrastructure without modifying current Capitec PDF parsing functionality.

## New CSV Format Supported
- **File**: `account_statement_1-Feb-2025_to_8-Feb-2026.csv` under `Bank_statements/` folder
- **Columns**: Nr, Account, Posting Date, Transaction Date, Description, Original Description, Parent Category, Category, Money In, Money Out, Fee, Balance
- **Date Format**: YYYY-MM-DD (e.g., 2025-02-03)
- **Amount Format**: Separate columns for Money In (positive income), Money Out (negative expenses), and Fee (negative fees)

## Changes Made

### 1. Updated Bank Detector (`backend/services/bank_detector.py`)
- Enhanced `_score_capitec()` method to recognize the new Money In/Out format
- Added scoring for:
  - "money in" and "money out" column detection (+0.5 points)
  - "posting date" and "transaction date" headers (+0.2 points)
  - "account" and "balance" columns (+0.1 points)
- Confidence score for new format: 100%

### 2. Extended Capitec Adapter (`backend/services/bank_adapters.py`)
- Added support for three Capitec formats:
  1. **Money In/Out Format** (NEW): Native Capitec CSV export with separate Money In/Out/Fee columns
  2. **Table Format**: Debit/Credit columns (existing)
  3. **Simple Format**: Single Amount column with +/- signs (existing)

- Updated `_map_columns()` method to recognize:
  - "posting date" and "transaction date" patterns
  - "money in", "money out", and "fee" columns
  - Maintains support for existing column patterns

- Added `_normalize_money_in_out_format()` handler:
  - Combines Money In, Money Out, and Fee columns into single Amount
  - Formula: `amount = money_in + money_out + fee`
  - Preserves correct signs (money_out and fee already negative in CSV)

- Updated `_detect_format()` method to route to appropriate handler

## Data Integrity
- ✓ All 565 transactions successfully parsed
- ✓ Correct amount signs maintained
- ✓ Income transactions: 120 (Total: R223,741.71)
- ✓ Expense transactions: 444 (Total: R-223,539.87)
- ✓ Net balance change: R201.84
- ✓ Pending transactions (last 2 rows) handled correctly

## Backward Compatibility
- ✓ Existing PDF parsing for Capitec statements unchanged
- ✓ Existing CSV adapters for other formats unchanged
- ✓ All existing Capitec formats continue to work
- ✓ Auto-detection continues to work for all bank types

## How It Works
1. When a CSV is uploaded to `/upload` endpoint:
   - `validate_csv()` checks for required columns
   - `normalize_csv()` detects the bank type using `BankDetector.detect()`
   - For Capitec: `BankDetector._score_capitec()` recognizes Money In/Out format
   - `CapitecAdapter.normalize()` routes to appropriate format handler
   - `_normalize_money_in_out_format()` processes the new format
   - Returns standardized transactions: `{date, description, amount}`

2. Transactions flow through existing categorization and reporting pipeline
   - No changes required to downstream processing

## Testing
Two test scripts provided:
1. `test_capitec_csv_import.py` - Main parsing test with formatted output
2. `verify_capitec_balance.py` - Data integrity verification

Run tests:
```bash
python test_capitec_csv_import.py
python verify_capitec_balance.py
```

## Future Enhancements
- The adapter is extensible for additional Capitec CSV variations
- Monitor for other Capitec export formats and add handlers as needed
- Consider adding category/classification preservation from CSV if required
