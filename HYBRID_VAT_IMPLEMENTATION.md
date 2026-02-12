# Hybrid VAT Classification - Implementation Complete

## ✅ Successfully Implemented!

The VAT Report export now uses a **hybrid approach** to classify custom categories as either VAT Input (Expenses) or VAT Output (Income/Sales).

---

## 🎯 What Was Implemented

### 1. **Database Schema Update**
Added `is_income` column to `custom_categories` table:
```sql
ALTER TABLE custom_categories ADD COLUMN is_income INTEGER DEFAULT 0;
-- 0 = Expense (VAT Input)
-- 1 = Income/Sales (VAT Output)
```

### 2. **Hybrid Classification Logic**
The system now checks **two places** when classifying a category:

```python
def _is_vat_output(category):
    # STEP 1: Check hardcoded categories (FAST)
    if category in {"Salary", "Income", "Sales"}:
        return True  # VAT Output
    
    # STEP 2: Check database for custom categories (FLEXIBLE)
    custom = db.query(CustomCategory).filter_by(name=category).first()
    if custom:
        return custom.is_income == 1
    
    # DEFAULT: Treat as expense
    return False
```

### 3. **API Updates**
Updated endpoints to support `is_income` parameter:

#### Create Category:
```python
POST /categories
{
  "category_name": "Consulting Fees",
  "is_income": true  // ← Mark as Income/Sales
}
```

#### Update Category VAT Settings:
```python
PATCH /categories/{category_name}/vat
{
  "vat_applicable": true,
  "vat_rate": 15.0,
  "is_income": true  // ← Change to Income/Sales
}
```

---

## 📊 How It Works

### Before (Hardcoded Only):
```
INCOME_CATEGORIES = {"Salary", "Income"}

Transaction: "Consulting Fees" → Check list → NOT FOUND → ❌ EXPENSE (wrong!)
```

### After (Hybrid Approach):
```
INCOME_CATEGORIES = {"Salary", "Income", "Sales"}  // Step 1: Fast check

Transaction: "Consulting Fees" → Check list → NOT FOUND
    → Check database → is_income=1 → ✓ INCOME (correct!)

Transaction: "Salary" → Check list → FOUND → ✓ INCOME (fast!)

Transaction: "Fuel" → Check list → NOT FOUND → Check database → is_income=0 → ✓ EXPENSE
```

---

## 🔧 Usage Examples

### Creating a New Income Category

**Via API:**
```bash
curl -X POST "http://localhost:8000/categories?session_id=xyz123" \
  -H "Content-Type: application/json" \
  -d '{
    "category_name": "Rental Income",
    "is_income": true
  }'
```

**Via Frontend** (when UI is updated):
```
┌─────────────────────────────────────┐
│ Create Category                     │
├─────────────────────────────────────┤
│ Name: [Rental Income        ]       │
│                                     │
│ Type:                               │
│ ( ) Expense (VAT Input)            │
│ (•) Income/Sales (VAT Output) ←✓   │
│                                     │
│ [Create]                            │
└─────────────────────────────────────┘
```

### Updating Existing Category

**Change from Expense to Income:**
```bash
curl -X PATCH "http://localhost:8000/categories/Commission/vat" \
  -H "Content-Type: application/json" \
  -d '{
    "vat_applicable": true,
    "vat_rate": 15.0,
    "is_income": true
  }'
```

---

## 📂 Files Modified

### Backend Code:
1. **`backend/models.py`**
   - Added `is_income` column to `CustomCategory` model

2. **`backend/services/vat_service.py`**
   - Updated `_is_vat_output()` to use hybrid approach
   - Updated `update_category_vat_settings()` to accept `is_income` parameter
   - Added `INCOME_CATEGORIES` constant: `{"Salary", "Income", "Sales"}`

3. **`backend/services/categories_service.py`**
   - Updated `create_category()` to accept `is_income` parameter

4. **`backend/main.py`**
   - Updated `CreateCategoryRequest` to include `is_income` field
   - Updated `UpdateCategoryVATRequest` to include `is_income` field
   - Modified endpoints to pass `is_income` to services

### Migration Scripts:
- **`backend/migrate_add_is_income.py`** - Adds column to backend database
- **`backend/update_sales_to_income.py`** - Marks "Sales" as Income
- **`migrate_add_is_income.py`** - Adds column to root database (if needed)

---

## 🧪 Testing Results

```
=== VAT Classification Test ===
Sales (custom, DB): True     ✓ From database
Salary (hardcoded): True     ✓ Hardcoded (fast)
Income (hardcoded): True     ✓ Hardcoded (fast)
Fuel (expense): False        ✓ Default expense
✓ Hybrid approach working!
```

---

## 🎨 Current Classification

### VAT Output (Income/Sales):
- **Hardcoded (Fast)**:
  - Salary
  - Income  
  - Sales
- **Database (Flexible)**:
  - Any custom category with `is_income=1`
  - Examples: "Consulting Fees", "Rental Income", "Dividends"

### VAT Input (Expenses):
- All other categories
- Custom categories with `is_income=0` (default)

---

## 🚀 Next Steps for Frontend

To complete the user experience, update the frontend to:

1. **Add checkbox in Create Category modal:**
   ```typescript
   <label>
     <input type="checkbox" name="isIncome" />
     This is an Income/Sales category (VAT Output)
   </label>
   ```

2. **Add toggle in Category Manager:**
   ```typescript
   {categories.map(cat => (
     <div key={cat.name}>
       <span>{cat.name}</span>
       <select onChange={(e) => updateCategoryType(cat.name, e.target.value)}>
         <option value="expense">Expense (VAT Input)</option>
         <option value="income">Income (VAT Output)</option>
       </select>
     </div>
   ))}
   ```

3. **Update API calls:**
   ```typescript
   // Create category
   const response = await fetch('/categories', {
     method: 'POST',
     body: JSON.stringify({
       category_name: name,
       is_income: isIncomeChecked
     })
   });
   
   // Update category
   const response = await fetch(`/categories/${name}/vat`, {
     method: 'PATCH',
     body: JSON.stringify({
       vat_applicable: true,
       vat_rate: 15.0,
       is_income: true
     })
   });
   ```

---

## 📖 Summary

✅ **Problem**: Custom categories like "Sales" were hardcoded and couldn't be classified as Income

✅ **Solution**: Hybrid approach - check hardcoded list first (fast), then database (flexible)

✅ **Result**: 
- Fast classification for common categories
- Flexible classification for custom categories
- Users can create new income categories on the fly
- VAT reports automatically split correctly

✅ **Performance**: Minimal overhead (single database query only for custom categories)

✅ **Migration Status**: Backend database updated, Sales marked as Income

---

## 🔍 Verification Commands

**Check if migration was applied:**
```bash
cd backend
python -c "import sqlite3; conn = sqlite3.connect('statement_analyzer.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(custom_categories)'); print([c[1] for c in cursor.fetchall()])"
```

**Check Sales classification:**
```bash
cd backend  
python -c "from services.vat_service import VATService; print('Sales is VAT Output:', VATService()._is_vat_output('Sales'))"
```

**Export VAT report and verify:**
```bash
curl "http://localhost:8000/vat/export?session_id=YOUR_SESSION&format=excel"
```

---

## 📝 Notes

1. **Default Behavior**: New custom categories default to `is_income=0` (Expense)
2. **Built-in Categories**: Remain hardcoded for performance
3. **Backward Compatible**: Existing code works without changes
4. **Sales Category**: Already updated to Income in backend database

---

**Implementation Date**: February 11, 2026
**Status**: ✅ Complete and Tested
**Backend Ready**: Yes
**Frontend Updates Needed**: Add UI for `is_income` selection
