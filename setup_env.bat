@echo off
echo ==========================================
echo AXIOM Environment Setup
echo ==========================================

echo Checking Python...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python not found or not in PATH.
    echo Please install Python 3.10+ and ensure it is in your PATH.
    echo If using App Execution Aliases, try 'manage app execution aliases' in Windows Settings.
    pause
    exit /b 1
)

echo.
echo Installing AI Service Dependencies...
echo Requirement file: services\ai\requirements.txt
pip install -r services\ai\requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Pip install failed. Please check your internet connection or python environment.
) else (
    echo [SUCCESS] Dependencies installed.
)

echo.
echo ==========================================
echo Docker Setup
echo ==========================================
echo To start infrastructure (Neo4j, Qdrant, Postgres), run:
echo docker-compose -f docker-compose.yml up -d

echo.
echo Setup script finished.
pause
