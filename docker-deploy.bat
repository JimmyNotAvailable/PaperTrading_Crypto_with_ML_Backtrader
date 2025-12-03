@echo off
REM Docker Deployment Script for Crypto ML Trading Project
REM This script builds and runs the entire project in Docker

echo ============================================================
echo   CRYPTO ML TRADING PROJECT - DOCKER DEPLOYMENT
echo   Phase 1-5: Complete System with Backtrader
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo [INFO] Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Stop and remove old containers
echo [INFO] Stopping old containers...
docker-compose down 2>nul

REM Build images
echo.
echo [INFO] Building Docker images...
echo [INFO] This may take 5-10 minutes on first build...
echo.
docker-compose build

if errorlevel 1 (
    echo.
    echo [ERROR] Docker build failed!
    echo [INFO] Check the error messages above
    pause
    exit /b 1
)

echo.
echo [OK] Build completed successfully!
echo.

REM Start infrastructure services first
echo [INFO] Starting infrastructure (Kafka, MongoDB)...
docker-compose up -d zookeeper kafka mongo

echo [INFO] Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

REM Initialize MongoDB
echo [INFO] Initializing MongoDB admin user...
docker-compose run --rm backtrader-engine python -c "from app.services.mongo_db import init_default_user; init_default_user()"

REM Start all application services
echo.
echo [INFO] Starting all application services...
docker-compose up -d

echo.
echo ============================================================
echo   DEPLOYMENT COMPLETE!
echo ============================================================
echo.
echo Services running:
echo   - Kafka UI:           http://localhost:8080
echo   - Backtrader Dashboard: http://localhost:8501 (Login: admin/admin123)
echo   - MongoDB:            localhost:27017
echo.
echo Phase 1-2: Market Data Producer    [RUNNING]
echo Phase 3:   ML Predictor             [RUNNING]
echo Phase 5:   Backtrader Engine        [RUNNING]
echo Phase 5:   Dashboard                [RUNNING]
echo.
echo View logs:   docker-compose logs -f [service-name]
echo Stop all:    docker-compose down
echo.
echo Press any key to view live logs (Ctrl+C to exit logs)...
pause >nul

docker-compose logs -f backtrader-engine ml-predictor market-data-producer
