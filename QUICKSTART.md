# Quick Start Guide

This guide will get you up and running in 5 minutes.

## Prerequisites

- Python 3.9+
- Node.js 18+
- Git

## Step 1: Start Backend

```bash
# Terminal 1 - Backend
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate
# Or Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Step 2: Start Frontend

```bash
# Terminal 2 - Frontend
cd frontend

npm install
npm run dev
```

You should see:
```
> Local:        http://localhost:3000
```

## Step 3: Test the App

1. Open http://localhost:3000 in your browser
2. Download the example CSV: `EXAMPLE_STATEMENT.csv` (in root)
3. Upload the CSV in the app
4. See transactions, summaries, and export options

## Example CSV Format

```csv
Date,Description,Amount
2024-01-15,SALARY DEPOSIT,-5000
2024-01-15,SHELL FUEL,250
2024-01-16,ESKOM ELECTRICITY,450
```

**Important:** 
- Negative amounts = Money out (expense)
- Positive amounts = Money in (income)

## API Testing

Test API endpoints directly:

```bash
# Health check
curl http://localhost:8000/health

# Get categories
curl http://localhost:8000/categories

# Upload a file (replace with actual file)
curl -X POST -F "file=@EXAMPLE_STATEMENT.csv" http://localhost:8000/upload
```

## Customizing Categories

Edit `backend/services/categoriser.py`:

```python
CATEGORIZATION_RULES = [
    {
        "category": "Rent",
        "keywords": ["rent", "landlord", "lease"],
        "exclude_keywords": []
    },
    # Add your own rules...
]
```

Then restart the backend server.

## Common Issues

### Port Already in Use
```bash
# Change port
uvicorn main:app --port 8001
# Update frontend .env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### CORS Error
The backend has CORS enabled for localhost. For production, update it in `main.py`.

### Frontend can't reach backend
- Check backend is running on port 8000
- Check firewall/antivirus isn't blocking
- Try http://localhost:8000/health in browser

## Next Steps

1. **Customize Categories** - Edit `backend/services/categoriser.py`
2. **Deploy Backend** - Use Uvicorn + Gunicorn for production
3. **Deploy Frontend** - Use Vercel, Netlify, or your own server
4. **Add Authentication** - For multi-user support
5. **Add PDF Support** - Extend parser.py

## File Structure

```
backend/
  services/
    categoriser.py    ← Edit this for custom rules
    parser.py         ← Add file format support here
    summary.py        ← Modify reporting logic
    
frontend/
  components/
    UploadSection.tsx ← Customize upload UI
    MonthlySummary.tsx ← Customize summary display
```

## Production Checklist

- [ ] Customize categories for your business
- [ ] Set up proper database (PostgreSQL recommended)
- [ ] Configure environment variables
- [ ] Set up SSL/HTTPS
- [ ] Configure CORS for your domain
- [ ] Test all edge cases with real data
- [ ] Set up logging and monitoring
- [ ] Backup and disaster recovery plan

## Support

Check README.md for full documentation.
