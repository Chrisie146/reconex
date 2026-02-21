# Local Development Quick Start Guide

## Overview
This setup allows you to develop locally without affecting the production Render configuration.

## Quick Start (Windows)

### 1. **First Time Setup**
```powershell
cd backend
.\run-local-dev.ps1
```

The script will:
- ✓ Create `.env` from `.env.local` (one-time setup)
- ✓ Create Python virtual environment
- ✓ Install dependencies
- ✓ Run database migrations
- ✓ Start FastAPI with auto-reload

### 2. **Subsequent Runs**
Just run:
```powershell
cd backend
.\run-local-dev.ps1
```

It will skip already-completed setup steps.

## Quick Start (Linux/macOS/WSL)

```bash
cd backend
bash run-local-dev.sh
```

## Access Your API

Once running:
- **API Endpoint**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Development Workflow

1. **Make code changes** → Auto-reload triggered automatically
2. **Check `/docs`** → Test endpoints in browser
3. **Run tests** locally before pushing
4. **Commit & push** → Render automatically deploys (unchanged config)

## Environment Configuration

Your `.env` file controls local behavior:

| Setting | Local | Production |
|---------|-------|-----------|
| Database | SQLite local file | PostgreSQL on Render |
| Storage | Local `/uploads/` folder | AWS S3 |
| Debug | Enabled | Disabled |
| CORS | localhost:3000 & :8000 | defined in render.yaml |

## Safety Guarantees

✅ `.env` is in `.gitignore` — Never committed  
✅ `render.yaml` is untouched — Always ready to deploy  
✅ Render reads its own environment vars — Completely isolated from local  
✅ One `git push origin main` to deploy — No config conflicts  

## Troubleshooting

### "ModuleNotFoundError: No module named 'uvicorn'"
```powershell
pip install -r requirements.txt
```

### "Database locked" or migration issues
```powershell
# Remove local database to reset
rm statement_analyzer.db
# Run the script again - will recreate from scratch
.\run-local-dev.ps1
```

### Port 8000 already in use
Edit `.env` and change `API_PORT=8001` (or any free port)
Then restart the script.

### Virtual environment activation issues
```powershell
# Manual activation
.\.venv\Scripts\Activate.ps1
# Then run uvicorn directly:
uvicorn main:app --reload
```

## Git Workflow

```bash
# Local development
git checkout -b feature/my-feature
# Make changes, test locally
...
# Commit without touching .env or render.yaml
git commit -m "feat: add new feature"
git push origin feature/my-feature

# Create PR, merge to main
# Render automatically deploys from main with production config
```

## Next Steps

- Copy `.env.local` content to `.env` if script doesn't do it automatically
- Start the dev server: `.\run-local-dev.ps1`
- Open http://localhost:8000/docs in browser
- Start developing!
