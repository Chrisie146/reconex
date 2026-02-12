# Custom Categories - Persistence Fix

## Issue
Custom categories were disappearing when loading a new bank statement because they were stored in memory tied to a specific session ID. Each new statement upload creates a new session, causing the loss of previously created categories.

## Solution
Custom categories are now persisted in the database, making them available across all sessions.

## Changes Made

### 1. Database Model (`backend/models.py`)
- Added new `CustomCategory` table to store custom categories permanently:
  ```python
  class CustomCategory(Base):
      __tablename__ = "custom_categories"
      id = Column(Integer, primary_key=True, index=True)
      name = Column(String, nullable=False, unique=True, index=True)
      created_at = Column(DateTime, default=datetime.utcnow)
  ```

### 2. Categories Service (`backend/services/categories_service.py`)
- Modified `get_all_categories()` to load custom categories from database instead of in-memory storage
- Updated `create_category()` to save categories to database
- Updated `delete_category()` to remove categories from database
- Categories now persist across all sessions automatically

## Benefits
✅ Custom categories persist when you upload new bank statements  
✅ Categories are shared across all sessions  
✅ No data loss when switching between different bank statements  
✅ Categories survive server restarts  

## Usage
No changes needed in your workflow. Simply:
1. Create custom categories in the Categories page
2. Upload a new bank statement
3. Your custom categories will still be available!

## Database Migration
The new `custom_categories` table was automatically created when the backend restarted.
All future custom categories will be stored persistently.

## Testing
Run the test to verify persistence:
```bash
cd backend
python test_custom_categories_persistence.py
```

This should show that categories created in one session are available in all other sessions.
