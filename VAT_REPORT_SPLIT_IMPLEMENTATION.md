# VAT Report Export - Input/Output Split Implementation

## Overview
The VAT Report export functionality has been enhanced to split transactions between **VAT Input (Expenses)** and **VAT Output (Sales/Income)**, providing a clearer breakdown for South African VAT compliance reporting.

## Changes Made

### 1. **New Constants**
Added `INCOME_CATEGORIES` set in `backend/services/vat_service.py`:
```python
INCOME_CATEGORIES = {"Salary", "Income"}
```
This defines which categories represent VAT Output (sales/income) rather than VAT Input (expenses).

### 2. **New Helper Methods**
Added two new methods to the `VATService` class:

#### `_is_vat_output(category: str) -> bool`
- Determines if a transaction is VAT Output (income) or VAT Input (expense)
- Returns `True` for income categories, `False` for expense categories

#### `_split_transactions_by_type(transactions: List[Transaction]) -> Tuple[List[Transaction], List[Transaction]]`
- Splits a list of transactions into two lists:
  1. VAT Input transactions (expenses)
  2. VAT Output transactions (sales/income)

### 3. **Enhanced CSV Export**
The `_export_vat_csv()` method now:
- ✅ Creates separate sections for VAT Input and VAT Output
- ✅ Shows individual transactions for each type
- ✅ Calculates subtotals for Input expenses
- ✅ Calculates subtotals for Output income
- ✅ Displays Net VAT Position:
  - VAT Claimable (from Input/Expenses)
  - VAT Payable (from Output/Sales)
  - Net VAT to Claim/Pay
- ✅ Shows summary statistics

Example CSV structure:
```
VAT REPORT
Period: 2024-01-01 to 2024-12-31

VAT INPUT (Expenses) - VAT Claimable
Date,Description,Category,Merchant,Amount (Incl VAT),VAT Amount,Amount (Excl VAT)
...transactions...
INPUT SUBTOTALS,...

VAT OUTPUT (Sales/Income) - VAT Payable
Date,Description,Category,Merchant,Amount (Incl VAT),VAT Amount,Amount (Excl VAT)
...transactions...
OUTPUT SUBTOTALS,...

VAT SUMMARY
Total Transactions: X
  - Input (Expenses): Y
  - Output (Sales/Income): Z

NET VAT POSITION
VAT Claimable (Input): R X.XX
VAT Payable (Output): R X.XX
Net VAT (To Claim/Pay): R X.XX
```

### 4. **Enhanced Excel Export**
The `_export_vat_excel()` method now:
- ✅ Creates color-coded sections for visual clarity:
  - **Section Headers**: Green background (VAT Input & VAT Output)
  - **Data Headers**: Blue background
  - **Subtotals**: Light green background
  - **Net VAT Position**: Light red background for emphasis
- ✅ Separate data sections with transaction lists
- ✅ Individual subtotals for each section
- ✅ Comprehensive summary section including:
  - Transaction counts by type
  - VAT claimable and payable amounts
  - Net VAT position
  - Total amounts for Input and Output

### 5. **Category Classification**
Current classification:
- **VAT Input (Expenses)**:
  - Fuel
  - Bank Fees
  - Rent
  - Groceries
  - Utilities
  - Transport
  - Healthcare
  - Insurance
  - Entertainment
  - Clothing
  - Dining
  - Travel
  - Education
  - Other
  - Custom categories (by default)

- **VAT Output (Sales/Income)**:
  - Salary
  - Income
  - (Can be extended by adding more categories to `INCOME_CATEGORIES`)

## Features

### For Accountants/Finance Teams:
1. **Clear Compliance Structure**: Separate Input and Output for SARS VAT reporting
2. **Net VAT Calculation**: Automatic calculation of net position (VAT to claim or pay)
3. **Visual Organization**: Color-coded Excel sections for easy reading
4. **Detailed Breakdown**: Full transaction listings with VAT amounts

### For Business Analysis:
1. **Income Analysis**: See total sales/income and associated VAT
2. **Expense Analysis**: See total expenses and VATable amounts
3. **Net Position**: Understand VAT liability or claim at a glance

## Usage

The VAT Report export remains accessible through:
- **API Endpoint**: `/vat/export`
- **Query Parameters**:
  - `session_id`: Optional session identifier
  - `client_id`: Optional client identifier
  - `start_date`: Optional filter (YYYY-MM-DD format)
  - `end_date`: Optional filter (YYYY-MM-DD format)
  - `format`: "excel" (default) or "csv"

Example:
```
GET /vat/export?session_id=xyz&format=excel
GET /vat/export?client_id=123&start_date=2024-01-01&end_date=2024-12-31&format=csv
```

## Configuration Notes

### Adding More Income Categories
To add additional income categories (e.g., "Donations", "Grants"), edit the `INCOME_CATEGORIES` set:

```python
INCOME_CATEGORIES = {"Salary", "Income", "Donations", "Grants"}
```

### Customizing VAT Rates
VAT rates per category can be modified in `BUILT_IN_CATEGORY_VAT_DEFAULTS`:

```python
BUILT_IN_CATEGORY_VAT_DEFAULTS = {
    "Salary": {"applicable": False, "rate": 0.0},  # Income usually no VAT
    "Fuel": {"applicable": True, "rate": 15.0},    # Standard 15% VAT
    # ... other categories
}
```

## Testing

The implementation includes:
1. **Unit Tests**: Category classification (✓ Passed)
2. **Split Logic Tests**: Transaction splitting (✓ Passed)
3. **Integration**: Works with existing database and export endpoints

### Test Results:
```
✓ Salary: Output=True - Income category
✓ Fuel: Output=False - Expense category
✓ Groceries: Output=False - Expense category
✓ All tests completed successfully!
```

## Technical Details

### Files Modified:
- `backend/services/vat_service.py`
  - Added constants and helper methods
  - Updated `_export_vat_csv()` method
  - Updated `_export_vat_excel()` method

### Dependencies:
- No new dependencies added
- Uses existing: openpyxl, csv, BytesIO

### Performance:
- Single-pass transaction processing
- Minimal memory overhead (splits into two lists)
- No database query changes

## Future Enhancements

Potential improvements:
1. **Sales Tax Rates**: Support different VAT rates for different categories
2. **Export Formats**: Add PDF export with formatted layout
3. **Multi-period Reports**: Compare VAT across periods
4. **Custom Categories**: Allow users to define their own income/expense categories
5. **VAT Filing**: Direct integration with SARS eFiling format
6. **Threshold Tracking**: Monitor VAT registration threshold requirements

## South African VAT Context

### VAT Input vs Output:
- **VAT Input**: VAT charged on purchases/expenses. Can be claimed as a credit against VAT liability
- **VAT Output**: VAT charged on sales/income. Must be paid to SARS
- **Net VAT**: Difference between Input and Output. If positive, amount owed to SARS; if negative, refund due

### Reporting Requirements:
- Transactions split by Input/Output
- Non-VATable items clearly identified
- Monthly or quarterly filing to SARS
- Detailed records for audit purposes

This implementation aligns with South African tax compliance requirements (SARS VAT Act, 1991).

---

## Version History

- **v1.0** (Current) - Initial implementation with Input/Output split for VAT compliance reporting
