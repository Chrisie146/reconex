# Running Balance Feature

## Overview
Added a running balance column to the Transactions Table with user-configurable opening balance.

## Features

### 1. **Toggle Running Balance Column**
   - Checkbox in the filter panel: "Show Running Balance"
   - Displays/hides the running balance column in the transaction table
   - Column only renders when enabled to avoid unnecessary DOM overhead

### 2. **Opening Balance Input**
   - Number input field that appears when "Show Running Balance" is enabled
   - Allows users to set the starting balance
   - Default value: 0.00
   - Supports positive and negative values
   - Step: 0.01 (two decimal places)

### 3. **Running Balance Calculation**
   - Calculates cumulative balance for each transaction in the sorted order
   - Formula: `Running Balance = Opening Balance + Sum of all previous transactions`
   - Calculated dynamically based on current sort order
   - Updates automatically when:
     - Opening balance is changed
     - Transactions are sorted differently
     - Running balance toggle is enabled/disabled

### 4. **Visual Display**
   - **Positive Balance**: Green text (income net position)
   - **Negative Balance**: Red text (overdraft/negative position)
   - Formatted as: `R1,234,567.89` (South African locale)
   - Positioned in the rightmost column with right alignment
   - Displays after Invoice column

## Implementation Details

### Component: `TransactionsTable.tsx`

#### State Variables Added:
```tsx
const [showRunningBalance, setShowRunningBalance] = useState(false)
const [openingBalance, setOpeningBalance] = useState<string>('0')
```

#### New Function:
```tsx
const calculateRunningBalance = (txns: Transaction[]) => {
  const balanceMap = new Map<number, number>()
  let balance = parseFloat(openingBalance) || 0
  
  txns.forEach((txn) => {
    balance += txn.amount
    balanceMap.set(txn.id, balance)
  })
  
  return balanceMap
}
```

#### UI Components:
1. **Toggle Checkbox** in filter panel (shows when filters are open)
2. **Opening Balance Input** (shows when running balance is enabled)
3. **Running Balance Column Header** (conditional render)
4. **Running Balance Cell Data** (conditional render)

## Usage

1. Click **Filters** button in the transaction table header
2. Under the filter options, find **"Show Running Balance"** checkbox
3. Check the box to enable running balance display
4. Enter the **Opening Balance** (defaults to 0.00)
5. View the running balance for each transaction as you move through the list
6. Balances update dynamically as you:
   - Change the opening balance
   - Sort transactions by different columns
   - Filter transactions

## Design Considerations

- **Responsive**: Opening balance input appears/disappears with toggle
- **Performance**: Running balance calculated only when enabled
- **Accuracy**: Calculations respect transaction sort order (important when dates are out of order)
- **Localization**: Uses South African locale for formatting (en-ZA)
- **Color Coding**: Red/Green for quick visual assessment of balance status
- **No Backend Changes**: Feature is 100% frontend-only

## Example Scenario

```
Opening Balance: R50,000.00

Transaction 1: -R1,000.00  → Running Balance: R49,000.00 (green)
Transaction 2: +R5,000.00  → Running Balance: R54,000.00 (green)
Transaction 3: -R60,000.00 → Running Balance: R-6,000.00 (red/overdraft)
Transaction 4: +R2,000.00  → Running Balance: R-4,000.00 (red)
```

## Browser Compatibility
Works in all modern browsers supporting:
- React Hooks (useState, useEffect)
- ES6+ JavaScript
- CSS Grid/Flexbox
