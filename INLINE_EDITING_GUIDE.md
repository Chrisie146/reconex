# Inline Editing Guide

## Overview
The Transaction Table now supports **inline editing** for quick edits without modal popups, significantly improving user experience.

## Features

### 1. **Inline Category Editing**
- **Click** on any category cell to enter edit mode
- A dropdown appears with all available categories
- **Keyboard Shortcuts:**
  - `Enter` - Save the change
  - `Escape` - Cancel the edit
- **Apply to Similar** - Button (⟳) to apply category to all similar transactions
- **Save** (✓) or **Cancel** (✕) buttons are always visible

### 2. **Inline Merchant Editing**
- **Click** on any merchant cell to enter edit mode
- Type or paste the merchant name directly
- **Keyboard Shortcuts:**
  - `Enter` - Save the merchant name
  - `Escape` - Cancel the edit
- Shows "Add merchant" placeholder for empty cells
- **Save** (✓) or **Cancel** (✕) buttons appear during edit

### 3. **Visual Feedback**
- Cells show a **pencil icon (✎)** on hover to indicate they're editable
- Active editing cells have a **blue border** for clarity
- Status message appears briefly when edits are saved

## Usage Examples

### Editing a Category
1. Hover over the Category column
2. Click the cell
3. Select a category from the dropdown
4. Press `Enter` or click ✓ to save
5. Or click ✕ or press `Escape` to cancel

### Adding a Merchant Name
1. Hover over the Merchant column
2. Click the cell (shows "Add merchant" if empty)
3. Type the merchant name
4. Press `Enter` or click ✓ to save
5. The table updates instantly

### Applying Category to Similar
1. Edit a category cell
2. While in edit mode, click the ⟳ button
3. Opens "Categorize Filtered" modal with similar transactions
4. Apply the category to all matches in bulk

## Keyboard Shortcuts
| Action | Shortcut |
|--------|----------|
| Save edit | `Enter` |
| Cancel edit | `Escape` |
| Exit table hover | Click elsewhere |

## Tips for Power Users
- **Quick bulk editing**: Use "Apply to similar" for categories
- **Batch merchant assignment**: Use "Assign Merchant" button for filtered transactions
- **Fast workflow**: Chain edits using keyboard shortcuts instead of clicking buttons
- **No modals**: Everything happens inline, keeping focus on the table

## Technical Details
- Changes are saved immediately to the server
- If save fails, a message appears (retryable through re-clicking)
- Undo functionality is still available for bulk operations
- Toast notifications show save confirmation
