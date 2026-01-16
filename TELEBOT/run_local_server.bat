@echo off
REM ===================================================
REM تشغيل بوت شحن الهاتف المحمول على السرفر المحلي
REM Mobile Recharge Bot - Local Server
REM ===================================================

setlocal enabledelayedexpansion

echo.
echo ====================================
echo   🤖 بوت شحن الهاتف المحمول
echo   Mobile Recharge Bot - Local Setup
echo ====================================
echo.

REM الذهاب إلى مجلد المشروع
cd /d "%~dp0mobile_recharge_bot_python"

echo [1/4] التحقق من Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت!
    echo ❌ Python is not installed!
    pause
    exit /b 1
)
echo ✅ Python مثبت

REM فحص البيئة الافتراضية
echo.
echo [2/4] إعداد البيئة الافتراضية...

if exist venv (
    echo ✅ البيئة الافتراضية موجودة
) else (
    echo 🔨 إنشاء البيئة الافتراضية...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ فشل إنشاء البيئة الافتراضية
        pause
        exit /b 1
    )
)

REM تفعيل البيئة الافتراضية
echo 🔌 تفعيل البيئة الافتراضية...
call venv\Scripts\activate.bat

REM تثبيت المتطلبات
echo.
echo [3/4] تثبيت المتطلبات...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ❌ فشل تثبيت المتطلبات
    pause
    exit /b 1
)
echo ✅ تم تثبيت جميع المتطلبات

REM التحقق من .env
echo.
echo [4/4] التحقق من الإعدادات...
if not exist .env (
    echo ❌ ملف .env غير موجود!
    echo ❌ .env file not found!
    pause
    exit /b 1
)
echo ✅ ملف الإعدادات موجود

REM عرض معلومات الاتصال
echo.
echo ====================================
echo   📡 معلومات السرفر المحلي
echo   Local Server Information
echo ====================================
echo.
echo 🌐 IP Address:  192.168.0.108
echo 🔌 Port:        8000
echo 📍 Webhook URL: http://192.168.0.108:8000/webhook
echo 💾 Database:    bot_data.db (SQLite)
echo.

REM تشغيل البوت
echo ⏳ جاري تشغيل البوت...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo ❌ حدث خطأ أثناء تشغيل البوت
    echo ❌ An error occurred while running the bot
    pause
    exit /b 1
)

pause
