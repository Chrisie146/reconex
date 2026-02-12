# User ID Fix - Learned Rules Persistence

## Problem
When users uploaded a new bank statement, their learned categorization rules would "disappear". This happened because:
- Each statement upload created a new `session_id` (UUID)
- Learned rules were stored with only the `session_id` as identifier
- When a new statement was uploaded with a new `session_id`, the old rules couldn't be accessed

## Solution
Implemented a **persistent user_id** that stays the same across all uploads:
- Added `user_id` column to `user_categorization_rules` table
- Modified learning service to use `user_id` as primary identifier
- Updated all API endpoints to accept optional `user_id` parameter
- Frontend generates and stores `user_id` in localStorage
- Backend defaults to `session_id` for backward compatibility

## Architecture

### Database Changes
```sql
-- New column added to user_categorization_rules table
user_id: String (indexed) - Persistent user identifier
session_id: String (nullable) - Optional session where rule was created
```

### Backend Changes
1. **models.py**: Added `user_id` column to `UserCategorizationRule`
2. **services/categorization_learning_service.py**: 
   - All methods now accept `user_id` as primary parameter
   - `session_id` kept for tracking which session created the rule
3. **main.py**:
   - Upload endpoints accept optional `user_id` parameter
   - Learned rules endpoints accept optional `user_id` parameter
   - Falls back to `session_id` for backward compatibility

### Frontend Changes
1. **lib/userId.ts**: New utility for managing persistent user_id
   - Generates UUID on first use
   - Stores in localStorage
   - Returns same ID across all sessions
2. **components/UploadSection.tsx**: Passes `user_id` to upload endpoints
3. **components/LearnedRulesManager.tsx**: Uses `user_id` instead of `session_id`

## Migration
A migration script was created and run:
```bash
python backend/migrate_add_user_id.py
```

This added the `user_id` column and migrated existing rules to a migration user_id to preserve them.

## Testing
Created test script: `backend/test_user_id_fix.py`

Results:
- ✅ Rules persist across different session_ids
- ✅ Rules are isolated per user_id
- ✅ Different users can't see each other's rules
- ✅ Auto-categorization works with persistent rules

## Usage Flow

### Before Fix (Broken)
```
1. User uploads Jan statement → session_1 created
2. User categorizes transactions → rules stored with session_1
3. User uploads Feb statement → session_2 created
4. Rules from session_1 NOT accessible → must recategorize everything ❌
```

### After Fix (Working)
```
1. Frontend generates user_id "abc123" → stored in localStorage
2. User uploads Jan statement → session_1 + user_id="abc123"
3. User categorizes transactions → rules stored with user_id="abc123"
4. User uploads Feb statement → session_2 + user_id="abc123"
5. Rules with user_id="abc123" automatically loaded → auto-categorization works ✅
```

## API Changes

### Upload Endpoints
```python
POST /upload?user_id=<uuid>
POST /upload_pdf?user_id=<uuid>
```

### Learned Rules Endpoints
```python
GET /learned-rules?user_id=<uuid>
PUT /learned-rules/{rule_id}?user_id=<uuid>
DELETE /learned-rules/{rule_id}?user_id=<uuid>
POST /learned-rules/apply?session_id=<uuid>&user_id=<uuid>
```

All endpoints fall back to `session_id` if `user_id` not provided for backward compatibility.

## Benefits
1. ✅ **Persistent Learning**: Rules survive across multiple statement uploads
2. ✅ **Time Saving**: Users only need to categorize similar transactions once
3. ✅ **Better UX**: Automatic categorization improves with each upload
4. ✅ **Privacy**: Each user's rules are isolated from others
5. ✅ **Backward Compatible**: Old code still works without user_id

## Future Enhancements
- [ ] User accounts and authentication (replace localStorage with database)
- [ ] Share learned rules across devices
- [ ] Import/export learned rules
- [ ] Rule suggestions based on common patterns
- [ ] Machine learning to improve pattern matching
