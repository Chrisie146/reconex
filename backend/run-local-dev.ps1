# Local Development Startup Script for Windows PowerShell
# Purpose: Set up and run the FastAPI backend locally with auto-reload
# Usage: .\run-local-dev.ps1

Write-Host "=== Bank Statement Analyzer - Local Development Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists, if not create it from .env.example
if (-not (Test-Path ".env")) {
    Write-Host "[*] .env not found. Creating from .env.example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[OK] .env created. Please review if needed." -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] .env.example not found. Please create .env manually." -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "[OK] .env file found" -ForegroundColor Green
}

# Check Python
Write-Host ""
Write-Host "[*] Checking Python installation..." -ForegroundColor Cyan
$python = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] $python" -ForegroundColor Green

# Create/activate virtual environment if needed
Write-Host ""
Write-Host "[*] Checking virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "[*] Activating virtual environment..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"
Write-Host "[OK] Virtual environment activated" -ForegroundColor Green

# Install/upgrade dependencies
Write-Host ""
Write-Host "[*] Installing/updating Python dependencies..." -ForegroundColor Cyan
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Run migrations
Write-Host ""
Write-Host "[*] Running database migrations..." -ForegroundColor Cyan
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Migration note (may be normal for first run)" -ForegroundColor Yellow
}
else {
    Write-Host "[OK] Migrations completed" -ForegroundColor Green
}

# Start the development server
Write-Host ""
Write-Host "=== Starting FastAPI development server ===" -ForegroundColor Green
Write-Host ""
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Interactive Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "OpenAPI Schema: http://localhost:8000/openapi.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start uvicorn with auto-reload
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
