@echo off
REM تشغيل السرفر المحلي
REM Local Server Startup

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo   Starting Mobile Recharge Bot - Local Server
echo   IP: 192.168.0.108
echo   Port: 8000
echo ============================================
echo.

python start_server.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start server
    pause
    exit /b 1
)
