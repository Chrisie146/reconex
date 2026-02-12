@echo off
REM verify_setup.bat - Verify the project structure is complete

echo.
echo Verifying Bank Statement Analyzer Setup...
echo.

setlocal enabledelayedexpansion
set CHECKS=0
set PASSED=0

REM Function to check file
:check_files

echo Checking directories...
for %%d in (backend backend\services backend\exports frontend frontend\app frontend\components) do (
    set /a CHECKS+=1
    if exist "%%d" (
        echo [OK] %%d\
        set /a PASSED+=1
    ) else (
        echo [MISSING] %%d\ 
    )
)

echo.
echo Checking documentation...
for %%f in (README.md QUICKSTART.md API.md DEPLOYMENT.md TESTING.md PROJECT_SUMMARY.md DOCS_INDEX.md START_HERE.md EXAMPLE_STATEMENT.csv) do (
    set /a CHECKS+=1
    if exist "%%f" (
        echo [OK] %%f
        set /a PASSED+=1
    ) else (
        echo [MISSING] %%f
    )
)

echo.
echo Checking backend files...
for %%f in (backend\main.py backend\models.py backend\requirements.txt backend\services\parser.py backend\services\categoriser.py backend\services\summary.py backend\services\__init__.py backend\exports\__init__.py) do (
    set /a CHECKS+=1
    if exist "%%f" (
        echo [OK] %%f
        set /a PASSED+=1
    ) else (
        echo [MISSING] %%f
    )
)

echo.
echo Checking frontend files...
for %%f in (frontend\package.json frontend\tsconfig.json frontend\tailwind.config.ts frontend\next.config.js frontend\.env.local frontend\app\layout.tsx frontend\app\page.tsx frontend\app\globals.css frontend\components\Header.tsx frontend\components\UploadSection.tsx frontend\components\MonthlySummary.tsx frontend\components\CategoryBreakdown.tsx frontend\components\TransactionsTable.tsx frontend\components\ExportButtons.tsx) do (
    set /a CHECKS+=1
    if exist "%%f" (
        echo [OK] %%f
        set /a PASSED+=1
    ) else (
        echo [MISSING] %%f
    )
)

echo.
echo Checking configuration...
set /a CHECKS+=1
if exist ".gitignore" (
    echo [OK] .gitignore
    set /a PASSED+=1
) else (
    echo [MISSING] .gitignore
)

echo.
echo ================================
echo Results: %PASSED% / %CHECKS% checks passed
echo ================================

if %PASSED% equ %CHECKS% (
    echo.
    echo [SUCCESS] Setup is complete!
    echo.
    echo Next steps:
    echo 1. Read START_HERE.md
    echo 2. Follow QUICKSTART.md
    echo 3. cd backend
    echo 4. python -m venv venv
    echo 5. venv\Scripts\activate
    echo 6. pip install -r requirements.txt
    echo 7. uvicorn main:app --reload
    exit /b 0
) else (
    set /a MISSING=%CHECKS%-%PASSED%
    echo.
    echo [ERROR] Setup incomplete (%MISSING% items missing)
    echo Check missing files above
    exit /b 1
)
