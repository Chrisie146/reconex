# Testing Checklist

Complete testing guide to validate all features before deployment.

## Pre-Testing Setup

1. **Clean start**
   ```bash
   # Remove old database
   rm backend/statement_analyzer.db
   
   # Fresh venv
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start services**
   ```bash
   # Terminal 1: Backend
   cd backend
   uvicorn main:app --reload --port 8000
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

3. **Open browser**
   - http://localhost:3000

---

## Feature Testing

### 1. File Upload

- [ ] **Successful upload**
  - Use: `EXAMPLE_STATEMENT.csv`
  - Expected: ✅ File processed, session ID returned
  - Check: Transaction count = 30

- [ ] **Invalid file format**
  - Upload: `.txt` file
  - Expected: ❌ Error message about CSV format

- [ ] **Missing required columns**
  - Create CSV with only: `Date,Description`
  - Expected: ❌ Error about missing Amount column

- [ ] **Empty file**
  - Create empty CSV
  - Expected: ❌ Error about empty CSV

- [ ] **File too large**
  - Create 6MB CSV
  - Expected: ❌ Error about 5MB limit

- [ ] **Drag and drop**
  - Drag `EXAMPLE_STATEMENT.csv` to upload area
  - Expected: ✅ File selected and uploaded

---

### 2. CSV Parsing

**Test with different formats:**

- [ ] **Date formats**
  ```csv
  Date,Description,Amount
  2024-01-15,Test,100
  15/01/2024,Test,100
  01/15/2024,Test,100
  15-01-2024,Test,100
  January 15, 2024,Test,100
  ```
  - Expected: ✅ All parsed correctly

- [ ] **Amount formats**
  ```csv
  Date,Description,Amount
  2024-01-15,Test,1000
  2024-01-15,Test,1000.50
  2024-01-15,Test,1,000
  2024-01-15,Test,R1000
  2024-01-15,Test,R$1000.50
  ```
  - Expected: ✅ All parsed as 1000 or 1000.50

- [ ] **Negative/Positive amounts**
  ```csv
  2024-01-15,SALARY,-5000
  2024-01-15,EXPENSE,250
  ```
  - Expected: ✅ Income=-5000, Expense=250

- [ ] **Alternative amount columns (Debit/Credit)**
  ```csv
  Date,Description,Debit,Credit
  2024-01-15,SALARY,0,5000
  2024-01-15,FUEL,250,0
  ```
  - Expected: ✅ Parsed correctly

---

### 3. Transaction Display

After uploading `EXAMPLE_STATEMENT.csv`:

- [ ] **Table loads**
  - Expected: ✅ All transactions displayed

- [ ] **Sorting by Date**
  - Click "Date" dropdown
  - Expected: ✅ Transactions sorted newest first

- [ ] **Sorting by Amount**
  - Click "Amount" dropdown  
  - Expected: ✅ Transactions sorted by amount (largest first)

- [ ] **Sorting by Category**
  - Click "Category" dropdown
  - Expected: ✅ Transactions sorted alphabetically by category

- [ ] **Transaction count**
  - Expected: ✅ Shows "30 transactions" in header

- [ ] **Color coding**
  - Positive amounts: ✅ Green
  - Negative amounts: ✅ Red

- [ ] **Date formatting**
  - All dates show as DD/MM/YYYY
  - Expected: ✅ 15/01/2024 format

---

### 4. Monthly Summary

- [ ] **Summary cards display**
  - Expected: 3 cards (Income, Expenses, Net Balance)

- [ ] **Income total**
  - Expected: ✅ R10,500.00 (from example)

- [ ] **Expenses total**
  - Expected: ✅ R9,480.50 (from example)

- [ ] **Net balance**
  - Expected: ✅ R1,019.50 (Income - Expenses)

- [ ] **Monthly breakdown table**
  - Expected: 3 months displayed

- [ ] **Month totals add up**
  - Sum of monthly income = overall income
  - Expected: ✅ Verified

- [ ] **Green/red color coding**
  - Positive balance: ✅ Green
  - Negative balance: ✅ Red

---

### 5. Category Breakdown

- [ ] **All categories shown**
  - Expected: Income, Rent, Utilities, Fuel, Groceries, Fees, Other

- [ ] **Amounts correct**
  ```
  Income: R10,500.00
  Rent: R7,000.00
  Utilities: R970.00
  Fuel: R580.00
  Groceries: R740.00
  Fees: R49.99
  Other: 0.00
  ```
  - Expected: ✅ Matches expected totals

- [ ] **Percentage calculation**
  - Total: R20,039.75 (approx)
  - Income %: 52.4%
  - Expected: ✅ Percentages sum to ~100%

- [ ] **Sorted by amount**
  - Expected: ✅ Largest categories first

---

### 6. Categorization

Upload test file with clear category keywords:

```csv
Date,Description,Amount
2024-01-15,SALARY DIRECT DEPOSIT,-5000
2024-01-15,SHELL FUEL,250
2024-01-16,ESKOM ELECTRICITY,450
2024-01-16,CHECKERS GROCERIES,320
2024-01-20,RENT PAYMENT,3500
2024-01-22,VODACOM INTERNET,200
2024-01-25,BANK SERVICE CHARGE,50
```

- [ ] **Salary → Income**
  - Expected: ✅ Category: Income

- [ ] **Shell → Fuel**
  - Expected: ✅ Category: Fuel

- [ ] **Eskom → Utilities**
  - Expected: ✅ Category: Utilities

- [ ] **Checkers → Groceries**
  - Expected: ✅ Category: Groceries

- [ ] **Rent → Rent**
  - Expected: ✅ Category: Rent

- [ ] **Vodacom → Utilities**
  - Expected: ✅ Category: Utilities

- [ ] **Bank charge → Fees**
  - Expected: ✅ Category: Fees

- [ ] **Unknown → Other**
  - Add transaction with random description
  - Expected: ✅ Category: Other

---

### 7. Exports

#### Export Transactions

- [ ] **Export button present**
  - Expected: ✅ Button visible

- [ ] **Export downloads file**
  - Click "Export Transactions"
  - Expected: ✅ File downloads as `.xlsx`

- [ ] **Excel file opens**
  - Expected: ✅ File opens in Excel/Sheets

- [ ] **Excel format correct**
  - Headers: Date, Description, Amount, Category
  - Expected: ✅ All columns present

- [ ] **Data in Excel**
  - Expected: ✅ All 30 transactions present

- [ ] **Total row**
  - Expected: ✅ Last row shows TOTAL with sum formula

- [ ] **Formatting**
  - Headers: Dark blue background
  - Amounts: Currency format
  - Expected: ✅ Professional appearance

#### Export Summary

- [ ] **Export button present**
  - Expected: ✅ Button visible

- [ ] **Export downloads file**
  - Click "Export Summary"
  - Expected: ✅ File downloads as `.xlsx`

- [ ] **Multiple sheets**
  - Expected: ✅ 2 sheets (Monthly Summary, Category Breakdown)

- [ ] **Sheet 1: Monthly Summary**
  - Columns: Month, Income, Expenses, Net
  - Expected: ✅ 3+ rows of data + overall row

- [ ] **Sheet 2: Category Breakdown**
  - Columns: Category, Total Amount
  - Expected: ✅ All categories listed with amounts

- [ ] **Formulas work**
  - Open export in Excel
  - Recalculate
  - Expected: ✅ Formulas calculate correctly

---

### 8. UI/UX

- [ ] **Header visible**
  - Logo and title present
  - Expected: ✅ Professional appearance

- [ ] **Upload area clear**
  - Drag and drop instructions visible
  - Expected: ✅ User understands what to do

- [ ] **Error messages clear**
  - Try invalid file
  - Expected: ✅ Message explains what's wrong

- [ ] **Loading states**
  - During upload: "Processing..."
  - During export: "Exporting..."
  - Expected: ✅ Clear feedback

- [ ] **Responsive design**
  - View on mobile (dev tools)
  - Expected: ✅ Readable on small screens

- [ ] **Colors professional**
  - No bright neon colors
  - Expected: ✅ Neutral accounting style

- [ ] **Footer visible**
  - Expected: ✅ Copyright info present

---

### 9. Multiple Sessions

- [ ] **Upload second file**
  - Create different CSV
  - Click "Upload New Statement"
  - Expected: ✅ First data cleared

- [ ] **New session ID**
  - Expected: ✅ Different from first upload

- [ ] **Transactions different**
  - Expected: ✅ New transactions displayed

- [ ] **Session isolation**
  - Expected: ✅ No cross-contamination

---

### 10. Error Scenarios

Test each error path:

- [ ] **Null bytes in CSV**
  - Expected: ✅ Handled gracefully

- [ ] **Very long descriptions**
  - Add 1000-char description
  - Expected: ✅ Truncated in table, full in export

- [ ] **Special characters**
  - Include: `&`, `<`, `>`, `"`, `'`
  - Expected: ✅ Escaped properly

- [ ] **Zero amount**
  - Add transaction with amount=0
  - Expected: ✅ Processed (likely "Other" category)

- [ ] **Duplicate transactions**
  - Add same transaction twice
  - Expected: ✅ Both kept (not deduplicated)

- [ ] **Very old dates**
  - Add date from 1900
  - Expected: ✅ Parsed correctly

- [ ] **Future dates**
  - Add date from 2099
  - Expected: ✅ Parsed correctly

---

### 11. Performance

- [ ] **Large file handling**
  - Create CSV with 5000 transactions
  - Upload
  - Expected: ✅ Processes within reasonable time

- [ ] **Table scrolling**
  - Scroll through large transaction table
  - Expected: ✅ Smooth, no lag

- [ ] **Export speed**
  - Export 5000+ transactions
  - Expected: ✅ Completes within 10 seconds

---

## API Testing

Test endpoints directly:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Get categories
curl http://localhost:8000/categories

# 3. Upload file
curl -X POST -F "file=@EXAMPLE_STATEMENT.csv" \
  http://localhost:8000/upload

# Store session ID from response as $SESSION

# 4. Get transactions
curl http://localhost:8000/transactions?session_id=$SESSION

# 5. Get summary
curl http://localhost:8000/summary?session_id=$SESSION

# 6. Get category summary
curl http://localhost:8000/category-summary?session_id=$SESSION

# 7. Export (returns binary)
curl http://localhost:8000/export/transactions?session_id=$SESSION \
  -o transactions.xlsx

# 8. Export summary
curl http://localhost:8000/export/summary?session_id=$SESSION \
  -o summary.xlsx
```

- [ ] All endpoints respond
- [ ] JSON is valid
- [ ] Status codes correct
- [ ] Error messages helpful

---

## Browser Compatibility

Test on:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

Expected: ✅ Works on all modern browsers

---

## Deployment Testing

Before deploying to production:

- [ ] Backend builds without errors
  ```bash
  pip install -r requirements.txt
  uvicorn main:app --host 0.0.0.0
  ```

- [ ] Frontend builds without errors
  ```bash
  npm run build
  ```

- [ ] Database creates fresh
  - [ ] Tables created
  - [ ] Indexes working

- [ ] CORS configured correctly
  - [ ] Frontend can reach backend
  - [ ] No cross-origin errors

- [ ] Environment variables set
  - Backend: DATABASE_URL (if PostgreSQL)
  - Frontend: NEXT_PUBLIC_API_URL

---

## Sign-Off Checklist

Before declaring ready for customers:

- [ ] All tests above pass
- [ ] No console errors
- [ ] No warnings in logs
- [ ] Example CSV processes correctly
- [ ] Exports look professional
- [ ] UI is intuitive
- [ ] Code is clean
- [ ] Documentation is complete
- [ ] Deployment guide works
- [ ] Performance is acceptable

---

## Notes

Add observations here during testing:

```
Test Date: ___________
Tester: ___________

Issues Found:
1. 
2. 
3. 

Performance Notes:
- Upload time for 1000 txns: 
- Export time for 1000 txns: 

Recommendations:
1.
2.
3.
```

---

**All tests passing? Ready to ship! 🚀**
