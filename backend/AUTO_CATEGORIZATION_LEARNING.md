# Auto-Categorization Learning Feature

## Overview

The auto-categorization learning feature automatically learns from user categorization decisions and applies those patterns to future transactions. This dramatically reduces the time users spend categorizing recurring merchants and transaction types.

## How It Works

### 1. Learning Phase (Immediate)

When a user assigns a category to a transaction, the system **immediately** learns patterns:

```
User action: Categorizes "WOOLWORTHS 123 CAPE TOWN" → Groceries

System learns 3 patterns:
  ✓ Exact match: "WOOLWORTHS 123 CAPE TOWN" → Groceries
  ✓ Merchant match: "WOOLWORTHS" → Groceries  
  ✓ Starts-with match: "WOOLWORTHS 123" → Groceries
```

### 2. Application Phase (On Upload)

When a new statement is uploaded, the system:
1. Loads all learned rules for that user/session
2. Matches transactions against learned patterns
3. Auto-assigns categories based on matches
4. Only leaves truly new/unknown transactions for manual categorization

### 3. Pattern Matching Priority

Rules are applied in order of specificity:

1. **Exact match** (highest priority) - Full description matches exactly
2. **Merchant match** - Extracted merchant name matches
3. **Starts-with** - Description starts with pattern
4. **Contains** (lowest priority) - Pattern appears anywhere in description

## API Endpoints

### Get Learned Rules

```http
GET /learned-rules?session_id={session_id}
```

**Response:**
```json
{
  "rules": [
    {
      "id": 1,
      "category": "Groceries",
      "pattern_type": "merchant",
      "pattern_value": "WOOLWORTHS",
      "confidence_score": 1.0,
      "use_count": 15,
      "enabled": true,
      "created_at": "2024-01-15T10:30:00",
      "last_used": "2024-01-20T14:22:00"
    }
  ],
  "total": 1
}
```

### Update Learned Rule

```http
PUT /learned-rules/{rule_id}?session_id={session_id}
```

**Body:**
```json
{
  "category": "NewCategory",
  "enabled": true,
  "pattern_value": "Updated pattern"
}
```

### Delete Learned Rule

```http
DELETE /learned-rules/{rule_id}?session_id={session_id}
```

### Apply Learned Rules

Manually apply learned rules to current transactions:

```http
POST /learned-rules/apply?session_id={session_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Auto-categorized 25 transaction(s)",
  "updated_count": 25,
  "suggestions": {
    "123": "Groceries",
    "124": "Fuel",
    "125": "Entertainment"
  }
}
```

## User Workflow

### First Upload

```
User uploads statement
  → Transactions categorized as "Other" (default)
  → User manually categorizes:
      • WOOLWORTHS → Groceries
      • NETFLIX → Entertainment  
      • SHELL → Fuel
      • etc.
  → System learns patterns immediately
```

### Second Upload (Next Month)

```
User uploads new statement
  → System auto-categorizes:
      ✓ WOOLWORTHS STELLENBOSCH → Groceries (learned)
      ✓ NETFLIX.COM → Entertainment (learned)
      ✓ SHELL STATION 456 → Fuel (learned)
      ⚠ SPOTIFY PREMIUM → Other (new, needs categorization)
  → User only categorizes NEW merchants
  → 80-90% time saved! 🎉
```

## Database Schema

```sql
CREATE TABLE user_categorization_rules (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,           -- Per-user persistence
    category TEXT NOT NULL,             -- Target category
    pattern_type TEXT NOT NULL,         -- 'exact', 'merchant', 'starts_with', 'contains'
    pattern_value TEXT NOT NULL,        -- Pattern to match
    confidence_score REAL DEFAULT 1.0,  -- Rule reliability (0.0-1.0)
    use_count INTEGER DEFAULT 0,        -- Application count
    created_at TIMESTAMP,               -- When learned
    last_used TIMESTAMP,                -- Last application
    enabled INTEGER DEFAULT 1           -- 1=active, 0=disabled
);

-- Indexes for performance
CREATE INDEX idx_user_cat_rules_session ON user_categorization_rules(session_id);
CREATE INDEX idx_user_cat_rules_pattern ON user_categorization_rules(pattern_type, pattern_value);
CREATE INDEX idx_user_cat_rules_enabled ON user_categorization_rules(enabled);
```

## Pattern Extraction Logic

### Merchant Extraction

The system extracts merchant names by:
1. Removing common prefixes (POS PURCHASE, DEBIT ORDER, etc.)
2. Extracting first meaningful word/phrase
3. Normalizing (uppercase, remove special chars)

**Examples:**
```
"POS PURCHASE WOOLWORTHS 123" → "WOOLWORTHS"
"DEBIT ORDER NETFLIX.COM" → "NETFLIX"
"SHELL FUEL STATION 456" → "SHELL"
```

### Description Normalization

For pattern matching:
1. Convert to uppercase
2. Remove extra whitespace
3. Remove special characters (except spaces and dots)

**Example:**
```
"woolworths   #123 cape-town" 
  → "WOOLWORTHS 123 CAPE TOWN"
```

## Frontend Integration

### Display Learned Rules

Create a "Learned Patterns" or "Auto-Categorization Rules" section in settings:

```javascript
// Fetch learned rules
const response = await fetch(`/learned-rules?session_id=${sessionId}`);
const { rules } = await response.json();

// Display in a table
rules.forEach(rule => {
  console.log(`${rule.pattern_value} → ${rule.category} (used ${rule.use_count} times)`);
});
```

### Edit Rule

Allow users to modify categories or disable rules:

```javascript
// Update rule
await fetch(`/learned-rules/${ruleId}?session_id=${sessionId}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    category: 'NewCategory',
    enabled: false
  })
});
```

### Manual Application

Add a "Re-apply Auto-Categorization" button:

```javascript
// Apply learned rules to current transactions
await fetch(`/learned-rules/apply?session_id=${sessionId}`, {
  method: 'POST'
});

// Refresh transactions list
```

## Benefits

### Time Savings
- **First upload**: Full manual categorization needed
- **Second upload**: 70-90% auto-categorized
- **Ongoing**: Only new merchants need categorization

### User Control
- View all learned patterns
- Edit or disable specific rules
- Delete unwanted patterns
- Re-apply rules at any time

### Persistence
- Rules stored per user/session in database
- Survives app restarts
- Shared across devices (same session)

### Accuracy
- Multiple pattern types increase match rate
- Confidence scoring (future enhancement)
- Usage tracking shows which rules are effective

## Migration

For existing databases, run:

```bash
python migrate_add_learning_table.py
```

Or the table will be created automatically on next app startup via SQLAlchemy.

## Testing

Run the demo script:

```bash
python test_learning_feature.py
```

This demonstrates the full workflow without requiring a running server.

## Future Enhancements

### 1. Confidence Scoring
Track rule accuracy and adjust confidence scores:
- Increase confidence when rule is repeatedly used
- Decrease when user overrides auto-categorization

### 2. Fuzzy Matching
Use string similarity for close matches:
```python
"WOOLWORTHS CAPE TOWN" ≈ "WOOLWRTHS CAPETOWN"  # Typo tolerance
```

### 3. Amount-Based Rules
Learn recurring amounts:
```python
"NETFLIX" + R99.00 → Entertainment (high confidence)
"NETFLIX" + R150.00 → Entertainment (lower confidence, price changed?)
```

### 4. Cross-User Learning (Optional)
Anonymized pattern sharing:
- "NETFLIX" → Entertainment (95% of users agree)
- Privacy-preserving aggregation

### 5. Smart Suggestions
When user categorizes a new merchant, suggest category based on similar merchants:
```
User categorizing "CHECKERS"
  → Suggestion: "Groceries" (because WOOLWORTHS, PICK N PAY → Groceries)
```

## Code Structure

```
backend/
├── models.py
│   └── UserCategorizationRule (new model)
├── services/
│   └── categorization_learning_service.py (new service)
├── main.py
│   ├── Import learning service
│   ├── Learn on category assignment (PUT /transactions/{id})
│   ├── Apply on upload (POST /upload, POST /upload_pdf)
│   └── New endpoints (/learned-rules/*)
├── test_learning_feature.py (demo)
└── migrate_add_learning_table.py (migration)
```

## Configuration

No configuration needed - feature is always active:
- Learning happens automatically on categorization
- Application happens automatically on upload
- Users can disable individual rules via UI

## Performance Considerations

### Database Indexes
Three indexes ensure fast lookups:
- `session_id` - Filter by user
- `pattern_type, pattern_value` - Fast pattern matching
- `enabled` - Skip disabled rules

### Rule Count
Typical user will have 50-200 learned rules:
- ~30 frequent merchants
- Multiple patterns per merchant (2-3)
- Performance impact: negligible

### Matching Speed
Pattern matching is O(n) where n = number of rules:
- Exact match: Hash lookup (very fast)
- Merchant/starts-with: Linear scan (fast for <500 rules)
- Optimize with caching if needed

## Privacy & Data

### Per-User Isolation
- Rules scoped by `session_id`
- No cross-user data sharing (by default)
- Each user builds their own pattern library

### Data Retention
- Rules persist indefinitely (unless user deletes)
- Could add cleanup for unused rules (e.g., >1 year old with use_count=0)

### Export/Import
Future feature: Allow users to export/import their learned rules for backup or transfer.

---

**Summary**: This feature dramatically improves UX by learning from user behavior and automating repetitive categorization tasks. Users spend time only on truly new transactions, making the app faster and more pleasant to use over time.
