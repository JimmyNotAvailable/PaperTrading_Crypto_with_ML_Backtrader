@echo off
REM Launcher for Streamlit Dashboard - Phase 5
REM Crypto ML Trading Bot

echo ===================================
echo   Crypto ML Trading Dashboard
echo   Phase 5: Streamlit Interface
echo ===================================
echo.

REM Activate virtual environment
echo [1/3] Activating virtual environment...
call crypto-venv\Scripts\activate.bat

REM Check if streamlit is installed
echo [2/3] Checking dependencies...
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo WARNING: Streamlit not found. Installing...
    pip install streamlit plotly streamlit-autorefresh pandas-ta
)

REM Launch dashboard
echo [3/3] Starting Streamlit dashboard...
echo.
echo Dashboard will open at: http://localhost:8501
echo Press Ctrl+C to stop
echo.

streamlit run app\dashboard\main.py --server.port 8501 --server.headless false

pause
