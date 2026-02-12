#!/bin/bash
# verify_setup.sh - Verify the project structure is complete

echo "🔍 Verifying Bank Statement Analyzer Setup..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter
CHECKS=0
PASSED=0

check_file() {
    CHECKS=$((CHECKS + 1))
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
    fi
}

check_dir() {
    CHECKS=$((CHECKS + 1))
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $1/ (MISSING)"
    fi
}

echo "📁 Checking directories..."
check_dir "backend"
check_dir "backend/services"
check_dir "backend/exports"
check_dir "frontend"
check_dir "frontend/app"
check_dir "frontend/components"

echo ""
echo "📄 Checking documentation..."
check_file "README.md"
check_file "QUICKSTART.md"
check_file "API.md"
check_file "DEPLOYMENT.md"
check_file "TESTING.md"
check_file "PROJECT_SUMMARY.md"
check_file "DOCS_INDEX.md"
check_file "START_HERE.md"
check_file "EXAMPLE_STATEMENT.csv"

echo ""
echo "🐍 Checking backend files..."
check_file "backend/main.py"
check_file "backend/models.py"
check_file "backend/requirements.txt"
check_file "backend/services/parser.py"
check_file "backend/services/categoriser.py"
check_file "backend/services/summary.py"
check_file "backend/services/__init__.py"
check_file "backend/exports/__init__.py"

echo ""
echo "⚛️ Checking frontend files..."
check_file "frontend/package.json"
check_file "frontend/tsconfig.json"
check_file "frontend/tailwind.config.ts"
check_file "frontend/next.config.js"
check_file "frontend/.env.local"
check_file "frontend/app/layout.tsx"
check_file "frontend/app/page.tsx"
check_file "frontend/app/globals.css"
check_file "frontend/components/Header.tsx"
check_file "frontend/components/UploadSection.tsx"
check_file "frontend/components/MonthlySummary.tsx"
check_file "frontend/components/CategoryBreakdown.tsx"
check_file "frontend/components/TransactionsTable.tsx"
check_file "frontend/components/ExportButtons.tsx"

echo ""
echo "⚙️ Checking configuration..."
check_file ".gitignore"

echo ""
echo "================================"
echo "Results: $PASSED / $CHECKS checks passed"
echo "================================"

if [ $PASSED -eq $CHECKS ]; then
    echo -e "${GREEN}✓ Setup is complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Read START_HERE.md"
    echo "2. Follow QUICKSTART.md"
    echo "3. Run: cd backend && python -m venv venv"
    echo "4. Run: source venv/bin/activate"
    echo "5. Run: pip install -r requirements.txt"
    echo "6. Run: uvicorn main:app --reload"
    exit 0
else
    MISSING=$((CHECKS - PASSED))
    echo -e "${RED}✗ Setup incomplete ($MISSING items missing)${NC}"
    echo "Check missing files above"
    exit 1
fi
