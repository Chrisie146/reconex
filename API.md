# API Documentation

Complete API reference for the Bank Statement Analyzer backend.

## Base URL

```
http://localhost:8000  (Development)
https://your-domain.com (Production)
```

## Endpoints

### Health Check

**GET /health**

Check if the API is running.

Response:
```json
{
  "status": "healthy"
}
```

### Get Categories

**GET /categories**

Get list of available transaction categories.

Response:
```json
{
  "categories": [
    "Rent",
    "Utilities", 
    "Fuel",
    "Groceries",
    "Fees",
    "Income",
    "Other"
  ]
}
```

---

## Upload & Processing

### Upload Bank Statement

**POST /upload**

Upload a CSV bank statement file for processing.

**Request:**
- Content-Type: multipart/form-data
- Body: `file` (CSV file, max 5MB)

**Example:**
```bash
curl -X POST -F "file=@statement.csv" http://localhost:8000/upload
```

**Response (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "transaction_count": 28,
  "categories": ["Rent", "Utilities", "Fuel", "Income", "Other"],
  "warnings": null
}
```

**Response (400):**
```json
{
  "detail": "Invalid CSV: Missing required 'Date' column"
}
```

**Errors:**
- `400` - Invalid CSV format or missing required columns
- `413` - File too large (>5MB)
- `422` - Invalid file type (not CSV)

---

## Data Retrieval

### Get All Transactions

**GET /transactions?session_id={session_id}**

Retrieve all transactions from an upload session.

**Query Parameters:**
- `session_id` (required): Session ID from upload response
- `q` (optional): Search term for case-insensitive substring match in description and amount
- `category` (optional): Filter by category
- `date_from` (optional): Filter transactions from this date (YYYY-MM-DD)
- `date_to` (optional): Filter transactions to this date (YYYY-MM-DD)

**Example:**
```bash
curl "http://localhost:8000/transactions?session_id=550e8400-e29b-41d4-a716-446655440000&q=250"
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "count": 28,
  "transactions": [
    {
      "id": 1,
      "date": "2024-01-15",
      "description": "SALARY DEPOSIT",
      "amount": -5000.00,
      "category": "Income"
    },
    {
      "id": 2,
      "date": "2024-01-15",
      "description": "SHELL FUEL STATION",
      "amount": 250.00,
      "category": "Fuel"
    }
  ]
}
```

**Fields:**
- `id`: Transaction ID (database)
- `date`: ISO format date (YYYY-MM-DD)
- `description`: Original transaction description
- `amount`: Numeric amount (negative=expense, positive=income)
- `category`: Assigned category

---

## Analytics & Summary

### Get Monthly Summary

**GET /summary?session_id={session_id}**

Get monthly breakdown with income, expenses, and category totals.

**Query Parameters:**
- `session_id` (required): Session ID

**Response:**
```json
{
  "months": [
    {
      "month": "2024-01",
      "total_income": 5000.00,
      "total_expenses": 4800.50,
      "net_balance": 199.50,
      "categories": {
        "Rent": 3500.00,
        "Utilities": 450.00,
        "Fuel": 280.50,
        "Groceries": 320.75,
        "Fees": 49.99,
        "Income": 5000.00,
        "Other": 199.25
      }
    },
    {
      "month": "2024-02",
      "total_income": 5500.00,
      "total_expenses": 4680.00,
      "net_balance": 820.00,
      "categories": {
        "Rent": 3500.00,
        "Utilities": 520.00,
        "Fuel": 300.00,
        "Groceries": 420.00,
        "Fees": 0.00,
        "Income": 5500.00,
        "Other": 0.00
      }
    }
  ],
  "overall": {
    "total_income": 10500.00,
    "total_expenses": 9480.50,
    "net_balance": 1019.50
  }
}
```

### Get Category Summary

**GET /category-summary?session_id={session_id}**

Get total amounts by category across all transactions.

**Query Parameters:**
- `session_id` (required): Session ID

**Response:**
```json
{
  "categories": {
    "Rent": 7000.00,
    "Utilities": 970.00,
    "Fuel": 580.00,
    "Groceries": 740.00,
    "Income": 10500.00,
    "Fees": 49.99,
    "Other": 199.25
  }
}
```

**Note:** Categories sorted by total amount descending.

---

## Exports

### Export Transactions to Excel

**GET /export/transactions?session_id={session_id}**

Download all transactions as an Excel file.

**Query Parameters:**
- `session_id` (required): Session ID

**Response:**
- Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- File download: `transactions_<session_id>.xlsx`

**Excel Format:**
| Date | Description | Amount | Category |
|------|-------------|--------|----------|
| 2024-01-15 | SALARY DEPOSIT | -5000.00 | Income |
| 2024-01-15 | SHELL FUEL | 250.00 | Fuel |
| ... | ... | ... | ... |
| TOTAL | | SUM | |

**Example:**
```bash
curl -o transactions.xlsx http://localhost:8000/export/transactions?session_id=550e8400-e29b-41d4-a716-446655440000
```

### Export Monthly Summary to Excel

**GET /export/summary?session_id={session_id}**

Download monthly summary as a multi-sheet Excel file.

**Query Parameters:**
- `session_id` (required): Session ID

**Response:**
- Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- File download: `summary_<session_id>.xlsx`

**Excel Sheets:**

**Sheet 1: Monthly Summary**
| Month | Total Income | Total Expenses | Net Balance |
|-------|--------------|-----------------|------------|
| 2024-01 | 5000.00 | 4800.50 | 199.50 |
| 2024-02 | 5500.00 | 4680.00 | 820.00 |
| OVERALL | 10500.00 | 9480.50 | 1019.50 |

**Sheet 2: Category Breakdown**
| Category | Total Amount |
|----------|--------------|
| Rent | 7000.00 |
| Income | 10500.00 |
| Utilities | 970.00 |
| ... | ... |
| TOTAL | 20039.75 |

---

## Input Formats

### CSV Format

**Required columns (case-insensitive):**
- `Date` - Transaction date
- `Description` - Transaction description
- `Amount` OR `Debit`/`Credit` - Transaction amount

**Date Formats Supported:**
- YYYY-MM-DD (2024-01-15)
- DD/MM/YYYY (15/01/2024)
- MM/DD/YYYY (01/15/2024)
- DD-MM-YYYY (15-01-2024)
- YYYY/MM/DD (2024/01/15)
- DD.MM.YYYY (15.01.2024)
- Month DD, YYYY (January 15, 2024)
- Mon DD, YYYY (Jan 15, 2024)

**Amount Formats:**
- Plain numbers: `1000`, `1000.50`
- With commas: `1,000`, `1,000.50`
- With currency: `R1000`, `R$1000.50`, `$1000`
- European format: `1.000,50` (parsed as 1000.50)

**Amount Convention:**
- Negative = Expense/Outflow
- Positive = Income/Inflow

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "detail": "Error description"
}
```

### Common Error Codes

| Code | Reason | Solution |
|------|--------|----------|
| 400 | Invalid CSV | Check column names and format |
| 400 | File too large | Keep file under 5MB |
| 404 | Session not found | Check session_id |
| 422 | Invalid file type | Upload CSV file |
| 500 | Server error | Check server logs |

---

## Examples

### Complete Workflow

```bash
# 1. Upload statement
SESSION=$(curl -s -X POST -F "file=@statement.csv" \
  http://localhost:8000/upload | jq -r '.session_id')

# 2. Get transactions
curl -s http://localhost:8000/transactions?session_id=$SESSION | jq '.'

# 3. Get summary
curl -s http://localhost:8000/summary?session_id=$SESSION | jq '.'

# 4. Export transactions
curl -s http://localhost:8000/export/transactions?session_id=$SESSION \
  -o transactions.xlsx

# 5. Export summary
curl -s http://localhost:8000/export/summary?session_id=$SESSION \
  -o summary.xlsx
```

### JavaScript/Axios Example

```javascript
import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Upload
async function uploadStatement(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await axios.post(`${API_URL}/upload`, formData);
  return response.data.session_id;
}

// Get transactions
async function getTransactions(sessionId) {
  const response = await axios.get(`${API_URL}/transactions`, {
    params: { session_id: sessionId }
  });
  return response.data.transactions;
}

// Get summary
async function getSummary(sessionId) {
  const response = await axios.get(`${API_URL}/summary`, {
    params: { session_id: sessionId }
  });
  return response.data;
}

// Export
async function exportTransactions(sessionId) {
  const response = await axios.get(
    `${API_URL}/export/transactions?session_id=${sessionId}`,
    { responseType: 'blob' }
  );
  
  const url = window.URL.createObjectURL(response.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'transactions.xlsx';
  a.click();
}
```

---

## Rate Limiting

Currently no rate limits (development). Production deployment should implement:
- 10 uploads/minute per IP
- 100 API requests/minute per session

---

## Support

For API issues or questions, check:
1. README.md for features overview
2. QUICKSTART.md for setup
3. This document for API details
4. Backend logs for errors
