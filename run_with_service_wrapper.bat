@echo off
REM تشغيل البوت عبر Service Wrapper (يعيد تشغيل البوت تلقائياً عند التعطل)
REM البديل من PowerShell script

cd /d "C:\Users\Hp\Desktop\TelegramStoreBot"

echo.
echo ========================================
echo   🤖 Telegram Store Bot Service
echo ========================================
echo.
echo البوت يعمل الآن في الخلفية...
echo سيتم إعادة تشغيله تلقائياً عند التعطل
echo.
echo لإيقاف البوت: اضغط Ctrl + C
echo.
echo ========================================
echo.

REM تحاول استخدام pythonw أولاً (بدون نافذة console)
pythonw.exe service_wrapper.py

REM إذا فشلت pythonw، استخدم python
if errorlevel 1 (
    echo ⚠️ محاولة استخدام python بدلاً من pythonw...
    python service_wrapper.py
)

pause

