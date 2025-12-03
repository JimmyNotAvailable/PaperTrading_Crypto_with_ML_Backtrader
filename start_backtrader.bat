@echo off
REM Start Backtrader Engine - Phase 5
REM This script runs the Backtrader trading engine that executes trades based on ML signals

echo ========================================
echo Starting Backtrader Engine (Phase 5)
echo ========================================
echo.

cd /d "%~dp0"

REM Activate virtual environment
call crypto-venv\Scripts\activate.bat

REM Check if MongoDB is running
echo [INFO] Checking MongoDB connection...
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000); client.server_info(); print('MongoDB OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] MongoDB not detected! Engine will fail without MongoDB.
    echo [INFO] Start MongoDB first or use MongoDB Atlas.
    echo.
    pause
)

REM Initialize MongoDB (create admin user if needed)
echo [INFO] Initializing MongoDB...
python -c "from app.services.mongo_db import init_default_user; init_default_user()"

echo.
echo [INFO] Starting Backtrader Engine...
echo [INFO] Listening to Kafka topics:
echo        - crypto.ml_signals (ML predictions)
echo        - crypto.commands (panic button)
echo.

REM Run Backtrader Engine
python app\consumers\backtrader_engine.py

pause
