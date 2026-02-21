#!/usr/bin/env bash
# Local Development Startup Script for Linux/macOS/WSL
# Purpose: Set up and run the FastAPI backend locally with auto-reload
# Usage: bash run-local-dev.sh

echo "════════════════════════════════════════════════════════"
echo "  Bank Statement Analyzer - Local Development Setup"
echo "════════════════════════════════════════════════════════"
echo ""

# Check if .env exists, if not create it from .env.example
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ .env created. IMPORTANT: Review and update paths if needed."
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
else
    echo "✓ .env file found"
fi

# Check Python
echo ""
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi
python3 --version
echo "✓ Python found"

# Create/activate virtual environment if needed
echo ""
echo "Checking virtual environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"

# Install/upgrade dependencies
echo ""
echo "Installing/updating Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# Run migrations
echo ""
echo "Running database migrations..."
python -m alembic upgrade head
if [ $? -ne 0 ]; then
    echo "⚠️  Migration warning (may be normal for first run)"
else
    echo "✓ Migrations completed"
fi

# Start the development server
echo ""
echo "════════════════════════════════════════════════════════"
echo "  🚀 Starting FastAPI development server..."
echo "════════════════════════════════════════════════════════"
echo ""
echo "📍 API: http://localhost:8000"
echo "📍 Docs: http://localhost:8000/docs"
echo "📍 OpenAPI: http://localhost:8000/openapi.json"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Start uvicorn with auto-reload
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
