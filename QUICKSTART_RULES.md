# Quick Start: Categories & Rules Management

Get started with the new category and rule management system in 5 minutes.

## Step 1: Access the Page

1. Upload a bank statement to get a **session ID**
2. Navigate to **http://localhost:3000/rules?session_id=YOUR_SESSION_ID**
   - Or click the "Rules" link in the navigation menu
   - System automatically detects your session ID

## Step 2: Create Custom Categories (Optional)

### In the Categories Tab:

1. Click **"+ Add Custom Category"**
2. Enter category name: e.g., "Office Supplies", "Home Maintenance"
3. Click **"Add"**
4. See it appear in your custom categories list
5. Use it when creating rules

## Step 3: Create Your First Rule

### In the Rules Tab:

1. Click **"+ Create Rule"**
2. Fill the form:
   ```
   Rule Name:      Grocery Stores
   Category:       Groceries
   Keywords:       spar
                   pick n pay
                   checkers
                   woolworths
   Priority:       5
   Auto-apply:     ✓ Checked
   ```
3. Click **"Create Rule"**
4. Rule appears in the rules list

## Step 4: Preview Before Applying

1. Find your rule in the list
2. Click **"👁️ Preview Matches"**
3. See how many transactions match
4. Review sample transactions
5. Check if keywords matched correctly

## Step 5: Bulk Apply Rules

1. After creating all your rules, click **"⚡ Bulk Apply Rules"**
2. Confirm when prompted
3. System applies rules to all transactions
4. Shows result: "X transactions categorized using Y rules"

## Common Rule Examples

### Grocery Stores
```
Name: Grocery Stores
Category: Groceries
Keywords: spar, pick n pay, checkers, woolworths, shoprite
Priority: 5
Auto-apply: ✓
```

### Fuel Stations
```
Name: Fuel Stations
Category: Fuel
Keywords: shell, bp, engen, aral, petrol, diesel, brandstof
Priority: 5
Auto-apply: ✓
```

### Restaurants & Dining
```
Name: Restaurants
Category: Dining
Keywords: restaurant, cafe, bistro, pizza, burger, sushi
Priority: 10
Auto-apply: ✗ (review before applying)
```

### Bank Charges
```
Name: Bank Charges
Category: Bank Fees
Keywords: bank charge, service fee, admin fee, transfer fee
Priority: 1
Auto-apply: ✓
```

### Rent & Property
```
Name: Rental Payment
Category: Rent
Keywords: rent, rental, property management, landlord
Priority: 3
Auto-apply: ✓
```

### Insurance & Medical
```
Name: Medical Expenses
Category: Healthcare
Keywords: pharmacy, clinic, doctor, dentist, medical, health
Priority: 20
Auto-apply: ✗
```

## Tips & Best Practices

### 1. **Keyword Strategy**
- Use **short, specific keywords**: "spar" instead of "Spar Supermarket"
- Include **variations**: "shell", "bp" for fuel
- Add **Afrikaans alternatives**: "brandstof" for "fuel"
- Don't use words that might match unrelated transactions

### 2. **Priority Matters**
```
Priority 1-5:   Highly specific rules (bank fees, salary)
Priority 10-20: Common transaction types (groceries, fuel)
Priority 50+:   Generic fallback rules
```

Rules with lower priority numbers apply first. Once a transaction matches, it stops checking.

### 3. **Preview Everything**
Always preview before bulk applying:
- Catches keyword spelling mistakes
- Prevents wrong categorizations
- Shows match percentages

### 4. **Auto-Apply vs Manual Review**
- ✓ **Auto-apply**: Certain categories (groceries, fuel, salary)
- ✗ **Manual review**: Uncertain categories (dining, entertainment)

### 5. **Language Support**
Rules work with:
- 🇬🇧 English keywords
- 🇿🇦 Afrikaans keywords
- Mixed in same rule
- Case-insensitive matching

### 6. **Managing Rules**
- **Edit**: Click rule, update form, click Save
- **Delete**: Click rule, click Delete
- **Disable**: Toggle the enabled checkbox
- **Statistics**: View rule statistics below bulk apply

## Keyboard Shortcuts

- `Enter` in keyword field → Add keyword to list
- `Delete` button → Remove keyword
- `Ctrl+A` → Select all keywords for editing

## Common Issues

### Keywords Not Matching?

1. **Check spelling**: Exact match required
   - ❌ "shop" does NOT match "spar"
   - ✓ "spar" matches "SPAR", "Spar", "spar"

2. **Check word boundaries**: 
   - ✓ "park" matches "parking lot", "parking fee"
   - ❌ Applies only if "park" is a complete word in the description

3. **Use preview first**: Always preview before bulk apply

4. **Try simpler keywords**: Instead of "Supermarket", try "spar" or "pick n pay"

### Too Many Matches?

1. Make keywords more specific
2. Add additional keywords that narrow the rule
3. Increase priority to be more selective
4. Review and delete unused rules

### Not Enough Matches?

1. Check actual transaction descriptions in your statement
2. Add the exact words from descriptions as keywords
3. Use shorter, simpler keywords
4. Preview to see what's missing

## Session Management

- Rules are **session-specific**: Each upload gets its own rules
- Rules are **in-memory**: Don't persist after closing browser
- Perfect for: Testing and ad-hoc categorization
- Future: Database persistence for permanent rules

## Next Steps

1. **📊 Analytics**: View transaction statistics after categorizing
2. **📁 Export**: Export categorized transactions to Excel
3. **🔄 Undo**: Revert bulk categorization if mistakes occur
4. **📝 Notes**: Add notes to transactions (future feature)

## Need Help?

- **Documentation**: See CATEGORIES_RULES_GUIDE.md
- **Examples**: Check Common Rule Examples above
- **Preview**: Use preview feature to debug rules
- **Test Data**: Upload sample statement to practice

---

**Created**: Latest version with full multilingual support
**Language Support**: English, Afrikaans
**Status**: Production-ready MVP
