# Auto-Categorization Learning - Frontend UI

## Overview

The frontend UI provides a user-friendly interface to view and manage auto-learned categorization patterns.

## Components Added

### LearnedRulesManager Component
**File**: `components/LearnedRulesManager.tsx`

Displays all learned categorization patterns with:
- 📊 Statistics dashboard (total patterns, active patterns, usage stats)
- 🎯 Pattern type indicators (Exact, Merchant, Starts With, Contains)
- ✏️ Edit category inline
- 🔌 Enable/disable individual patterns
- 🗑️ Delete unwanted patterns
- 🔄 Re-apply all rules button

### Navigation Integration

**Updated Files**:
- `app/rules/page.tsx` - Added "Learned Patterns" tab
- `components/Sidebar.tsx` - Added sidebar link to learned patterns

## User Flow

### 1. View Learned Patterns

Navigate to: **Settings → Learned Patterns**

Or: `/rules?session_id={sessionId}&tab=learned`

### 2. Manage Patterns

Each pattern shows:
```
🏪 Merchant | Matches extracted merchant name
"WOOLWORTHS"
→ Groceries | Used 15 times | Last used: Jan 20, 2024

[Enable/Disable] [Edit] [Delete]
```

### 3. Actions Available

- **Edit Category**: Click edit icon, change category, save
- **Enable/Disable**: Toggle to activate/deactivate pattern
- **Delete**: Remove pattern permanently
- **Re-Apply All**: Manually trigger auto-categorization on current transactions

## UI Features

### Statistics Dashboard
Shows at-a-glance metrics:
- Total learned patterns
- Active (enabled) patterns
- Total times patterns were used
- Average usage per pattern

### Pattern Type Visual Indicators
- 🎯 **Exact Match**: Matches identical descriptions
- 🏪 **Merchant**: Matches extracted merchant name
- ▶️ **Starts With**: Matches prefix patterns
- 🔍 **Contains**: Matches substring patterns

### Empty State
When no patterns learned yet:
- Helpful message explaining the feature
- Time savings estimate (70-90%)
- Encouragement to start categorizing

### Information Panel
Toggleable info panel explaining:
- How auto-learning works
- What triggers pattern creation
- How to manage patterns
- When rules are applied

## Styling

Uses Tailwind CSS with:
- Purple theme for learned patterns (distinguishes from manual rules)
- Gradient backgrounds for stats
- Smooth transitions and hover effects
- Responsive design

## API Integration

### Endpoints Used

```typescript
// Get all learned rules
GET /learned-rules?session_id={sessionId}

// Update a rule
PUT /learned-rules/{ruleId}?session_id={sessionId}
Body: { category: string, enabled: boolean }

// Delete a rule
DELETE /learned-rules/{ruleId}?session_id={sessionId}

// Apply all rules
POST /learned-rules/apply?session_id={sessionId}
```

## TypeScript Interfaces

```typescript
interface LearnedRule {
  id: number
  category: string
  pattern_type: string  // 'exact' | 'merchant' | 'starts_with' | 'contains'
  pattern_value: string
  confidence_score: number
  use_count: number
  enabled: boolean
  created_at: string
  last_used: string | null
}
```

## State Management

Uses React hooks:
- `useState` for component state
- `useEffect` for data fetching
- Local state for editing/loading states

## Error Handling

- Loading states with spinners
- Error messages with retry option
- Confirmation dialogs for destructive actions
- Success feedback on operations

## Accessibility

- Semantic HTML
- ARIA labels on buttons
- Keyboard navigation support
- Color contrast compliance
- Tooltip descriptions

## Testing Locally

1. Start backend:
```bash
cd backend
python -m uvicorn main:app --reload
```

2. Start frontend:
```bash
cd frontend
npm run dev
```

3. Upload a statement and categorize some transactions

4. Navigate to: **Rules → Learned Patterns** tab

5. View your auto-learned patterns!

## Screenshots Locations

### Main View
- Pattern list with enable/disable toggles
- Statistics at top
- Re-apply button

### Edit Mode
- Inline category editor
- Save/Cancel buttons

### Empty State
- Encouragement message
- Time savings estimate

## Future Enhancements

### Planned Features
1. **Search/Filter**: Filter patterns by category or type
2. **Bulk Operations**: Enable/disable multiple patterns
3. **Export/Import**: Backup and restore patterns
4. **Analytics**: Show time saved over months
5. **Pattern Preview**: Preview which transactions will match
6. **Confidence Visualization**: Show pattern reliability scores

### UI Improvements
1. Drag-and-drop to reorder
2. Pattern grouping by category
3. Visual diff when editing
4. Undo/redo operations
5. Pattern usage charts

## Integration Points

### With TransactionsTable
Future: Add "Auto" badge on auto-categorized transactions

### With Upload Flow
Future: Show auto-categorization stats after upload

### With Dashboard
Future: Add auto-categorization metrics widget

## Development Notes

### Component Structure
```
LearnedRulesManager/
├── Header (title, info button, stats)
├── Actions (re-apply, refresh)
└── Rules List
    └── Rule Card
        ├── Pattern info
        ├── Category display/edit
        └── Action buttons
```

### State Flow
```
Load → Fetch Rules → Display → User Action → Update → Refresh
```

### Performance
- Lazy loading for large rule sets (future)
- Optimistic updates for instant feedback
- Debounced search (future)

## Troubleshooting

### Rules not showing?
1. Check sessionId is in URL
2. Verify backend is running
3. Check browser console for errors
4. Try refreshing the page

### Can't edit rules?
1. Ensure sessionId matches
2. Check backend logs for errors
3. Verify API endpoint is accessible

### Re-apply not working?
1. Check for confirmation dialog
2. Look for success/error message
3. Check transactions were actually updated
4. Verify backend processed request

---

**Status**: ✅ Production Ready  
**Component**: `LearnedRulesManager.tsx`  
**Page**: `/rules?tab=learned`  
**Navigation**: Sidebar → Learned Patterns
