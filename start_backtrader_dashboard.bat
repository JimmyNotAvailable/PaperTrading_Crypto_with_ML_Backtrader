@echo off
REM Start Backtrader Dashboard - Phase 5
REM This script runs the Streamlit dashboard to monitor Backtrader performance

echo ========================================
echo Starting Backtrader Dashboard (Phase 5)
echo ========================================
echo.

cd /d "%~dp0"

REM Activate virtual environment
call crypto-venv\Scripts\activate.bat

REM Check if MongoDB is running
echo [INFO] Checking MongoDB connection...
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000); client.server_info(); print('MongoDB OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] MongoDB not detected! Dashboard will show empty data.
    echo [INFO] Start MongoDB first or use MongoDB Atlas.
    echo.
)

echo.
echo [INFO] Starting Dashboard...
echo [INFO] Dashboard will open at: http://localhost:8501
echo [INFO] Default Login: admin / admin123
echo.
echo [TIP] Press Ctrl+C to stop
echo.

REM Run Streamlit Dashboard
streamlit run app\dashboard\backtrader_app.py --server.headless true

pause
