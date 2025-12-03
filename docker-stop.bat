@echo off
REM Stop all Docker services

echo ============================================================
echo   STOPPING ALL SERVICES
echo ============================================================
echo.

cd /d "%~dp0"

echo [INFO] Stopping all containers...
docker-compose down

echo.
echo [OK] All services stopped
echo.
echo To remove volumes (DELETE ALL DATA):
echo   docker-compose down -v
echo.
pause
