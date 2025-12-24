@echo off
title Telegram Store Bot
color 0A
cls

echo =====================================================
echo    STARTING TELEGRAM STORE BOT
echo    Keep this window OPEN. 
echo    If you close this window, the bot will STOP.
echo =====================================================
echo.

:: Ensure we are in the script directory
cd /d "%~dp0"

:: Set Environment Variables for Cloud Database
set TELEGRAM_BOT_TOKEN=8562406465:AAEudEf_n6ZDnMlVy_UTwJ7eG1hBdDb1Tgw
set DATABASE_URL=postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway
set BOT_ADMIN_ID=1041977029

:: Run the bot
python bot.py

:: If it crashes, pause so user can see error
echo.
echo =====================================================
echo    BOT STOPPED
echo =====================================================
pause
