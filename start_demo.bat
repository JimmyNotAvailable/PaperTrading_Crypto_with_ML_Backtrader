@echo off
echo Starting Crypto ML Trading Bot Demo...
echo.

REM Start MongoDB and Demo
docker compose up -d mongo demo

REM Wait a bit
timeout /t 5 /nobreak

REM Show status
echo.
echo Container Status:
docker compose ps

echo.
echo Logs (press Ctrl+C to exit):
docker compose logs -f demo

