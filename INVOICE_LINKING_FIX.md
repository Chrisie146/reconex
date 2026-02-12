# Invoice-To-Transaction Linking Fix

## Problem
When users confirmed an invoice match, the invoice was NOT properly linked to the transaction. The `InvoiceMatch` table was updated with status='confirmed', but:

1. The `Transaction` table had no `invoice_id` field
2. There was no direct reference from transaction to invoice
3. API responses didn't include invoice information
4. Users couldn't see which transactions had confirmed invoices

## Solution Implemented

### 1. Database Schema Update
Added `invoice_id` column to `Transaction` table:

```python
# backend/models.py
class Transaction(Base):
    # ... existing fields ...
    invoice_id = Column(Integer, nullable=True)  # Link to confirmed invoice
    # ... rest of fields ...
```

**Migration Required:**
```sql
ALTER TABLE transactions ADD COLUMN invoice_id INTEGER NULL;
```

### 2. Backend Changes

#### Updated `confirm_match()` endpoint
When a user confirms or rejects an invoice match:

**File:** `backend/main.py` (lines ~1788-1805)

```python
if confirm:
    # ... existing code ...
    im.status = 'confirmed'
    im.confirmed_at = datetime.utcnow()
    
    # NEW: Link the transaction to the invoice
    txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
    if txn:
        txn.invoice_id = inv_id  # ✓ Sets invoice_id on transaction
else:
    # ... existing code ...
    im.status = 'rejected'
    
    # NEW: Remove invoice link if rejecting
    txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
    if txn:
        txn.invoice_id = None  # ✓ Clears invoice_id if rejected
```

#### Updated `GET /transactions` endpoint
Now includes `invoice_id` in response:

**File:** `backend/main.py` (line ~1430)

```python
return {
    "session_id": session_id,
    "count": len(transactions),
    "transactions": [
        {
            "id": t.id,
            "session_id": t.session_id,
            "statement_name": ...,
            "date": t.date.isoformat(),
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "invoice_id": t.invoice_id,  # ✓ NEW FIELD
            "merchant": ...
        }
        for t in transactions
    ]
}
```

#### Updated `get_transactions_by_category()` service
Now includes `invoice_id` in category queries:

**File:** `backend/services/summary.py` (line ~160)

```python
def get_transactions_by_category(...) -> List[Dict[str, Any]]:
    return [
        {
            "id": txn.id,
            "date": txn.date.isoformat(),
            "description": txn.description,
            "amount": txn.amount,
            "category": txn.category,
            "invoice_id": txn.invoice_id,  # ✓ NEW FIELD
        }
        for txn in transactions
    ]
```

### 3. Data Flow

**Before (Broken):**
```
User clicks "Confirm"
  ↓
POST /invoice/match/confirm
  ↓
InvoiceMatch.status = 'confirmed' ✓
Transaction.invoice_id = ??? ✗ (not set)
  ↓
Frontend has no way to know transaction is linked to invoice
```

**After (Fixed):**
```
User clicks "Confirm"
  ↓
POST /invoice/match/confirm
  ↓
InvoiceMatch.status = 'confirmed' ✓
Transaction.invoice_id = {invoice_id} ✓ (now set)
  ↓
GET /transactions includes invoice_id ✓
Frontend can display invoice information ✓
```

## Testing Checklist

### Database Migration
- [ ] Run SQL: `ALTER TABLE transactions ADD COLUMN invoice_id INTEGER NULL;`
- [ ] Verify column exists: `SELECT * FROM sqlite_master WHERE type='table' AND name='transactions';`

### Backend Testing
1. Upload invoice and run matching
2. Confirm match for an invoice
3. Query `GET /transactions?session_id={id}`
4. Verify response includes `invoice_id` field with correct value
5. Confirm another invoice and verify it updates correctly
6. Reject an invoice and verify `invoice_id` becomes NULL

### Frontend Testing
1. After confirming invoice, transaction should show invoice badge
2. Query `/transactions` and verify `invoice_id` is present
3. Transaction card should display linked invoice information

### Database Verification
```sql
-- Check confirmed invoices have transaction references
SELECT 
    im.id, 
    im.invoice_id, 
    im.transaction_id,
    t.invoice_id as txn_invoice_id,
    im.status
FROM invoice_matches im
LEFT JOIN transactions t ON im.transaction_id = t.id
WHERE im.status = 'confirmed'
ORDER BY im.confirmed_at DESC;
```

## Benefits

✅ **Direct Transaction-Invoice Link:** Transaction table now has direct reference to invoice  
✅ **Proper Data Integrity:** Linked data is persisted on transaction  
✅ **Better Queries:** Can query transactions with invoices without joins  
✅ **Cleaner API:** Invoice information available directly in transaction responses  
✅ **UI Enhancement:** Frontend can show which transactions have invoices  
✅ **Audit Trail:** Easy to see which transactions were matched to which invoices  

## Backward Compatibility

- ✓ Existing code continues to work
- ✓ `invoice_id` is nullable, so old transactions work fine
- ✓ Only new confirmations will populate `invoice_id`
- ✓ API responses gracefully handle missing `invoice_id`

## Future Enhancements

1. Add invoice details to transaction API responses for richer UI
2. Filter transactions by "has_invoice" parameter
3. Export transactions with invoice information to Excel
4. Show invoice preview in transaction detail view
5. Create accounting entries linked to confirmed invoices
