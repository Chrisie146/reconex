# Category & Rules Management System

Complete guide for the new category and rule management system with multilingual support.

## Overview

The Category & Rules Management system provides accountants and bookkeepers with an intuitive interface to:
- Create custom transaction categories
- Define smart rules using multilingual keywords
- Preview transaction matches before applying rules
- Bulk apply rules to categorize transactions automatically
- Track rule effectiveness with statistics

## Features

### 1. **Built-in Categories** (15 total)
- Fuel
- Bank Fees
- Rent
- Salary
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

### 2. **Custom Categories**
Create your own categories for specific business needs:
- Easily add new categories via the UI
- Delete custom categories anytime
- Use in rules immediately after creation

### 3. **Smart Rules**
Define keyword-based rules with multiple options:

#### Rule Properties
- **Name**: Descriptive rule name (e.g., "Grocery Stores")
- **Category**: Which category to assign when rule matches
- **Keywords**: One or more keywords to match (supports English & Afrikaans)
- **Priority**: Lower number = higher priority (matching stops at first match)
- **Auto-apply**: Automatically apply to new transactions or require approval

#### Multilingual Support
Rules work with keywords in both English and Afrikaans:
```
Keywords Examples:
- English: "spar", "pick n pay", "checkers"
- Afrikaans: "kruideniersware", "supermark", "winkel"
- Mixed: "fuel", "petrol", "diesel", "brandstof"
```

Matching is:
- **Case-insensitive**: "SPAR", "spar", "Spar" all match
- **Word-boundary aware**: "park" does not match "parking"
- **Deterministic**: Same keywords always produce same results

### 4. **Preview System**
Before applying rules, see:
- Number of transactions matching the rule
- Percentage of total transactions
- Sample transactions with matched keywords
- Which keyword caused the match

### 5. **Bulk Apply**
Apply multiple rules at once:
- Apply all enabled rules in priority order
- First match wins (stops matching for each transaction)
- See how many transactions were categorized
- How many rules were applied

### 6. **Rule Statistics**
Track rule effectiveness:
- Total matches per rule
- Percentage of transactions matched
- Helps identify unused or redundant rules

## Frontend Components

### 1. **Rules Page** (`frontend/app/rules/page.tsx`)
Main page with tab navigation:
- **Categories Tab**: Manage categories
- **Rules Tab**: Manage rules

Location: `/rules`

Features:
- Tab navigation between Categories and Rules
- Session ID detection from URL or localStorage
- Responsive design with Tailwind CSS

### 2. **Categories Manager** (`frontend/components/CategoriesManager.tsx`)
UI for category management:
- Add new custom category
- Delete custom categories
- View all built-in categories
- Error/success feedback

### 3. **Rules Manager** (`frontend/components/RulesManager.tsx`)
Complete rules management interface:
- Create new rules with form
- View all rules with keywords
- Edit rules (via form update)
- Delete rules
- Preview rule matches
- Bulk apply rules
- View rule statistics

## Backend Components

### 1. **Categories Service** (`backend/services/categories_service.py`)
Core business logic:

**Key Methods:**
- `create_category(session_id, name)` - Create custom category
- `delete_category(session_id, category_name)` - Delete custom category
- `create_rule(session_id, rule_data)` - Create new rule
- `update_rule(session_id, rule_id, rule_data)` - Update existing rule
- `delete_rule(session_id, rule_id)` - Delete rule
- `get_rules(session_id)` - Get all rules for session
- `get_categories(session_id)` - Get all categories
- `preview_rule_matches(session_id, rule_id, transactions)` - Preview matches
- `apply_rules_to_transactions(session_id, transactions, auto_apply_only)` - Apply rules
- `get_rule_statistics(session_id, transactions)` - Get statistics

**Storage:**
- Session-scoped in-memory storage
- Each session has isolated rules and categories
- Perfect for MVP; can migrate to database later

### 2. **API Endpoints** (`backend/main.py`)

#### Categories
- `GET /categories?session_id={id}` - Get all categories
- `POST /categories?session_id={id}` - Create custom category
- `DELETE /categories/{name}?session_id={id}` - Delete category

#### Rules
- `GET /rules?session_id={id}` - Get all rules
- `POST /rules?session_id={id}` - Create rule
- `PUT /rules/{rule_id}?session_id={id}` - Update rule
- `DELETE /rules/{rule_id}?session_id={id}` - Delete rule
- `POST /rules/{rule_id}/preview?session_id={id}` - Preview matches
- `POST /rules/apply-bulk?session_id={id}` - Apply rules in bulk
- `GET /rules/statistics?session_id={id}` - Get statistics

## Usage Examples

### Creating a Rule for Grocery Stores

1. Go to `/rules` page
2. Click "⚙️ Rules" tab
3. Click "+ Create Rule"
4. Fill form:
   - Name: "Grocery Stores"
   - Category: "Groceries"
   - Keywords:
     ```
     spar
     pick n pay
     checkers
     checkers liqour
     woolworths
     shoprite
     ```
   - Priority: 5 (high priority)
   - Auto-apply: ✓ enabled
5. Click "Create Rule"

### Previewing Before Applying

1. Find the rule in the list
2. Click "👁️ Preview Matches"
3. See sample transactions that would be matched
4. Review for accuracy

### Bulk Categorizing Transactions

1. Create all your rules
2. Click "⚡ Bulk Apply Rules"
3. Confirm when prompted
4. System categorizes all matching transactions
5. See results: "X transactions categorized using Y rules"

## Multilingual Keyword Matching

### How It Works

The system uses the `multilingual.match_keyword_in_text()` function:

1. **Keyword normalization**: Remove whitespace, convert to lowercase
2. **Text normalization**: Clean transaction description
3. **Word boundary matching**: Uses regex `\b...\b` for exact word matches
4. **Case-insensitive**: "Spar" matches "SPAR"
5. **No translation**: Uses keywords as-is without translation

### Examples

**Rule: Fuel Stations**
- Keywords: ["shell", "bp", "engen", "petrol", "diesel", "brandstof"]
- Matches: ✅ "Shell Petrol Station", "BP Diesel", "Brandstof Engen"
- No match: ❌ "Shelf Life Store" (boundary check prevents partial matches)

**Rule: Groceries (Multilingual)**
- Keywords: ["spar", "pick n pay", "checkers", "kruideniersware"]
- Matches: ✅ "Spar Supermarket", "Pick n Pay Food", "Kruideniersware Thabazimbi"
- Works for: ✅ Both English and Afrikaans statements

## Technical Details

### Rule Matching Algorithm

```
For each rule in priority order (lowest number = highest priority):
  1. For each keyword in rule:
     a. Check if keyword matches any word in transaction description
     b. Use word boundary matching (case-insensitive)
  2. If ANY keyword matches:
     a. Return this category immediately (first match wins)
     b. Stop checking remaining rules for this transaction
     
If no rules match:
  Category = "Other" (default fallback)
```

### Priority System

Rules are applied in priority order:
- Lower priority number = applies first
- Common/specific rules: priority 1-10
- General rules: priority 20-50
- Fallback rules: priority 100+

Example:
```
Priority 5:  "Shell/BP" → Fuel (specific)
Priority 10: "Gas/Petrol" → Fuel (general)
Priority 50: "Any expense" → Utilities (fallback)
```

## Data Model

### Rule Object
```json
{
  "rule_id": "uuid-string",
  "name": "Grocery Stores",
  "category": "Groceries",
  "keywords": ["spar", "pick n pay", "checkers"],
  "priority": 5,
  "auto_apply": true,
  "enabled": true
}
```

### Preview Object
```json
{
  "rule_name": "Grocery Stores",
  "category": "Groceries",
  "count": 42,
  "percentage": 15.7,
  "matched": [
    {
      "id": 1,
      "date": "2024-01-15",
      "description": "Spar Supermarket",
      "amount": 1500.00,
      "keyword_matched": "spar"
    }
  ]
}
```

## Session Management

Rules and categories are **session-scoped**:
- Each upload/session has isolated rules
- Rules don't persist between sessions
- Perfect for testing before deployment

To persist rules permanently, implement database storage in CategoriesService.

## Future Enhancements

1. **Database Persistence**
   - Save rules to PostgreSQL/SQLite
   - Share rules across sessions
   - Version control for rule changes

2. **Advanced Matching**
   - Regex pattern support
   - Amount-based rules
   - Date-range rules
   - Multi-condition rules (AND/OR logic)

3. **Rule Management**
   - Export/import rule sets
   - Rule templates for industries
   - Conflict detection and resolution
   - Rule conflict logs

4. **Analytics**
   - Rule usage statistics
   - Match distribution charts
   - Uncategorized transaction analysis

5. **Collaboration**
   - Share rules between users
   - Rule approval workflows
   - Audit logs for changes

## Troubleshooting

### Rules Not Matching

1. **Check keyword spelling**
   - Exact match required (no fuzzy matching)
   - Case-insensitive but spelling-sensitive

2. **Word boundary issues**
   - "park" won't match "parking"
   - Add "parking" as separate keyword if needed

3. **Priority conflicts**
   - Rule with higher priority might match first
   - Adjust priority to change order

### Preview Shows Nothing

1. Session might have no transactions
2. Keywords might not match any descriptions
3. Transaction descriptions might be abbreviated
4. Try simpler keywords or exact transaction text

## API Testing

Run the end-to-end test:

```bash
cd backend
python test_categories_rules_e2e.py
```

This tests:
- Session creation
- Category retrieval and creation
- Rule creation with multilingual keywords
- Rule preview
- Bulk apply
- Statistics
- Rule update and deletion

## Integration Points

### With Bulk Categorizer
The `bulk_categorizer.py` uses:
- `multilingual.match_keyword_in_text()` for keyword matching
- `multilingual.handle_ocr_text()` for OCR safety
- Same algorithm as rules system

### With Parser
The parser validates multilingual column headers using:
- `multilingual.normalize_headers()`
- Supports English and Afrikaans headers
- Raises `ColumnDetectionError` if ambiguous

### With PDF Parser
PDF extraction uses:
- `multilingual.normalize_headers()` for FNB tables
- Converts output to canonical headers
- Works with Afrikaans FNB statements

## Support & Questions

For issues or questions about:
- **Rules functionality**: See RulesManager component
- **Categories**: See CategoriesManager component
- **Backend logic**: See categories_service.py
- **Multilingual support**: See multilingual.py
- **API endpoints**: See main.py (FastAPI application)
