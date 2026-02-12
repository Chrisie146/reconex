# Bank Statement Analyzer - Production Ready MVP

A professional-grade bank statement analysis tool for small businesses. Process CSV bank statements, categorize transactions automatically, and export detailed reports.

## Features

✅ **CSV Upload & Validation** - Support for multiple date formats and amount formats
✅ **Automatic Categorization** - Rule-based transaction categorization (editable)
✅ **Monthly Summaries** - Income, expenses, and net balance per month
✅ **Category Analysis** - Breakdown of spending by category
✅ **Excel Export** - Accountant-ready Excel reports
✅ **Professional UI** - Clean, accounting-style interface

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv

# Activate venv (Windows)
venv\Scripts\activate
# Or (Mac/Linux)
source venv/bin/activate

pip install -r requirements.txt

# Run the API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## CSV Format

Your bank statement must be in CSV format with these columns:

| Column | Description | Format |
|--------|-------------|--------|
| **Date** | Transaction date | Any common format (YYYY-MM-DD, DD/MM/YYYY, etc.) |
| **Description** | Transaction description | Any text |
| **Amount** or **Debit/Credit** | Transaction amount | Number (can include currency symbol) |

### Example CSV

```csv
Date,Description,Amount
2024-01-15,SALARY DEPOSIT,-5000
2024-01-15,SHELL FUEL STATION,250
2024-01-16,CHECKERS GROCERIES,350
2024-01-16,ESKOM ELECTRICITY,450
2024-01-20,RENT PAYMENT,3500
```

**Amounts:**
- Negative = Expenses (outflow)
- Positive = Income (inflow)

**Alternative Format (Debit/Credit):**
```csv
Date,Description,Debit,Credit
2024-01-15,SALARY DEPOSIT,0,5000
2024-01-15,SHELL FUEL,250,0
```

## API Endpoints

### Upload Statement
```
POST /upload
- Body: multipart/form-data with 'file' (CSV)
- Returns: { session_id, transaction_count, categories }
```

### Get Transactions
```
GET /transactions?session_id=<session_id>
- Returns: List of all transactions
```

### Get Monthly Summary
```
GET /summary?session_id=<session_id>
- Returns: Monthly totals and category breakdown
```

### Get Category Totals
```
GET /category-summary?session_id=<session_id>
- Returns: Total amounts by category
```

### Export Transactions
```
GET /export/transactions?session_id=<session_id>
- Returns: Excel file with all transactions
```

### Export Summary
```
GET /export/summary?session_id=<session_id>
- Returns: Excel file with monthly summary and category breakdown
```

## Customizing Categories

Edit `backend/services/categoriser.py` to add or modify categorization rules:

```python
CATEGORIZATION_RULES = [
    {
        "category": "Rent",
        "keywords": ["rent", "landlord", "lease"],
        "exclude_keywords": []
    },
    # Add more rules...
]
```

**How it works:**
1. Keywords are matched against transaction descriptions (case-insensitive)
2. First matching rule wins
3. Exclude keywords prevent false positives
4. Default category is "Other"

## Project Structure

```
backend/
  ├── main.py                 # FastAPI application
  ├── models.py              # SQLAlchemy database models
  ├── services/
  │   ├── parser.py          # CSV parsing and validation
  │   ├── categoriser.py     # Transaction categorization
  │   └── summary.py         # Summary calculations & Excel export
  ├── exports/
  └── requirements.txt

frontend/
  ├── app/
  │   ├── layout.tsx         # Root layout
  │   ├── page.tsx           # Main page
  │   └── globals.css        # Global styles
  ├── components/
  │   ├── Header.tsx
  │   ├── UploadSection.tsx
  │   ├── MonthlySummary.tsx
  │   ├── CategoryBreakdown.tsx
  │   ├── TransactionsTable.tsx
  │   └── ExportButtons.tsx
  ├── tailwind.config.ts
  ├── package.json
  └── .env.local
```

## Technical Details

### Database
- SQLite with SQLAlchemy ORM
- One Transaction table with session-based data isolation
- No authentication (stateless MVP)

### Date Parsing
Supports: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, YYYY/MM/DD, DD.MM.YYYY, Month DD YYYY formats

### Amount Parsing
Automatically handles:
- Currency symbols (R, $, €, £)
- Commas as thousands separator
- Commas or dots as decimal separators

## Production Deployment

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run with Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000

# Or use Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Frontend
```bash
npm install
npm run build
npm start
```

### Environment Variables

**.env.local** (Frontend):
```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

## Limitations & Future Enhancements

### Current (MVP)
- Single-session, stateless operation
- No user authentication
- SQLite database (suitable for single-server deployments)
- Rule-based categorization only

### Future Enhancements
- PDF statement support
- User authentication & subscriptions
- Multi-currency support
- Recurring transaction detection
- Budget forecasting
- Multi-database support (PostgreSQL, MySQL)
- Batch file processing
- Advanced reporting & analytics

## Troubleshooting

### "Invalid CSV: Missing required 'Date' column"
- Ensure your CSV has a column named "Date" exactly (or date, DATE)
- Check for trailing spaces in column names

### Export returns 403 error
- Ensure your backend has write permissions
- Check CORS is properly configured

### Frontend can't connect to backend
- Verify backend is running on port 8000
- Check NEXT_PUBLIC_API_URL in .env.local
- Test `curl http://localhost:8000/health`

## Support & Licensing

This is a production MVP suitable for deployment. Code is professional-grade with clear documentation and error handling.

For customization or deployment support, contact your development team.
