@echo off
REM تشغيل البوت بشكل مستمر 24/7
REM إذا توقف البوت، سيتم إعادة تشغيله تلقائياً

title Telegram Store Bot - 24/7
color 0A

setlocal enabledelayedexpansion

cd /d "C:\Users\Hp\Desktop\TelegramStoreBot"

:loop
cls
echo.
echo ================================================
echo     Telegram Store Bot - 24/7 Mode
echo ================================================
echo.
echo الوقت: %date% %time%
echo تاريخ اليوم: %date%
echo.
echo [*] جاري تشغيل البوت...
echo.

REM تفعيل البيئة الافتراضية
call .venv\Scripts\activate.bat

REM تشغيل البوت
python bot.py

echo.
echo ================================================
echo البوت توقف في: %time%
echo سيتم إعادة التشغيل في 5 ثوانٍ...
echo اضغط Ctrl+C لإيقاف النافذة بشكل نهائي
echo ================================================
echo.

REM انتظر 5 ثوانٍ قبل إعادة المحاولة
timeout /t 5 /nobreak

REM عودة للحلقة
goto loop

pause
