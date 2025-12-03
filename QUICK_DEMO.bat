@echo off
echo ====================================
echo CRYPTO ML TRADING BOT - QUICK DEMO
echo ====================================
echo.
echo Chon loai demo:
echo.
echo 1. Mock Demo (Khong can Discord token) - KHOI CHAY NGAY
echo 2. Run Bot That (Can Discord token)
echo 3. Docker Demo (Production-like)
echo 4. Thoat
echo.
set /p choice="Nhap lua chon (1-4): "

if "%choice%"=="1" goto mock_demo
if "%choice%"=="2" goto real_bot
if "%choice%"=="3" goto docker_demo
if "%choice%"=="4" goto end

:mock_demo
echo.
echo Dang chay Mock Demo...
echo.
python mock_bot_demo.py
pause
goto end

:real_bot
echo.
echo Kiem tra token...
if not exist token.txt (
    echo [ERROR] File token.txt khong ton tai!
    echo Vui long tao file token.txt voi Discord bot token.
    pause
    goto end
)
echo.
echo Dang khoi dong bot...
python run_bot_demo.py
pause
goto end

:docker_demo
echo.
echo Kiem tra Docker...
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop chua chay!
    echo Vui long khoi dong Docker Desktop truoc.
    pause
    goto end
)
echo.
echo Dang khoi dong Docker containers...
docker compose up -d mongo demo
echo.
echo Xem logs (Press Ctrl+C de thoat):
docker compose logs -f demo
goto end

:end
echo.
echo Cam on da su dung!
pause

