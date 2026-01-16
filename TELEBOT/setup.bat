@echo off
REM ============================================
REM بوت شحن الهاتف المحمول - سكريبت التثبيت
REM ============================================

echo.
echo ╔════════════════════════════════════════════╗
echo ║   بوت شحن الهاتف المحمول - نسخة محلية   ║
echo ╚════════════════════════════════════════════╝
echo.

REM تحقق من تثبيت PHP
php -v >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ خطأ: PHP غير مثبت أو غير متاح في PATH
    echo الحل: ثبّت XAMPP أو أضف PHP إلى متغير البيئة
    pause
    exit /b 1
)

echo ✅ PHP متاح
php -v

echo.
echo ════════════════════════════════════════════
echo 1️⃣  التحقق من الإضافات المطلوبة...
echo ════════════════════════════════════════════
echo.

REM التحقق من MySQLi
php -m | find /i "mysqli" >nul
if %errorlevel% equ 0 (
    echo ✅ MySQLi: متاح
) else (
    echo ❌ MySQLi: غير متاح - فعّله في php.ini
)

REM التحقق من cURL
php -m | find /i "curl" >nul
if %errorlevel% equ 0 (
    echo ✅ cURL: متاح
) else (
    echo ❌ cURL: غير متاح - فعّله في php.ini
)

echo.
echo ════════════════════════════════════════════
echo 2️⃣  اختبار الاتصال بقاعدة البيانات...
echo ════════════════════════════════════════════
echo.

REM اختبر الاتصال
php -r "
\$conn = @mysqli_connect('localhost', 'root', '', 'mr');
if (\$conn) {
    echo '✅ الاتصال بقاعدة البيانات: نجح' . PHP_EOL;
    \$result = mysqli_query(\$conn, 'SELECT COUNT(*) as count FROM bot');
    \$row = mysqli_fetch_assoc(\$result);
    echo 'عدد الجداول المتاحة: ' . \$row['count'] . PHP_EOL;
    mysqli_close(\$conn);
} else {
    echo '❌ فشل الاتصال بقاعدة البيانات' . PHP_EOL;
    echo 'تأكد من:' . PHP_EOL;
    echo '  - MySQL مُشغّل' . PHP_EOL;
    echo '  - قاعدة البيانات mr موجودة' . PHP_EOL;
    echo '  - اسم المستخدم: root كلمة المرور: فارغة' . PHP_EOL;
}
"

echo.
echo ════════════════════════════════════════════
echo 3️⃣  فحص الملفات المطلوبة...
echo ════════════════════════════════════════════
echo.

setlocal enabledelayedexpansion
set files=config.php xindex.php Control\main.class.php cronjob.php

for %%F in (%files%) do (
    if exist "mobilerechargev2 2\mobilerechargev2\%%F" (
        echo ✅ %%F: موجود
    ) else (
        echo ❌ %%F: غير موجود
    )
)

echo.
echo ════════════════════════════════════════════
echo 4️⃣  فحص إعدادات API_KEY...
echo ════════════════════════════════════════════
echo.

php -r "
\$configFile = 'mobilerechargev2 2\mobilerechargev2\config.php';
if (file_exists(\$configFile)) {
    \$content = file_get_contents(\$configFile);
    if (preg_match('/define\(['\''\"']API_KEY['\''\"].*?['\''\"']([^'\''\"]*)/', \$content, \$matches)) {
        \$token = \$matches[1];
        if (strlen(\$token) > 50) {
            echo '✅ API_KEY: مُعرّف (تم العثور على Token صحيح)' . PHP_EOL;
        } else {
            echo '⚠️  API_KEY: قد لا يكون صحيحاً - يرجى التحقق' . PHP_EOL;
        }
    }
}
"

echo.
echo ════════════════════════════════════════════
echo ✅ انتهى الفحص الأولي
echo ════════════════════════════════════════════
echo.
echo 📋 الخطوات التالية:
echo.
echo 1. تأكد من تشغيل MySQL (من XAMPP Control Panel)
echo 2. غيّر API_KEY في config.php بـ Token البوت الصحيح
echo 3. شغّل الخادم باختيار أحد الخيارات أدناه:
echo.
echo    الخيار A - استخدام Apache (XAMPP):
echo    - انسخ المشروع إلى C:\xampp\htdocs\mobilerechargev2
echo    - شغّل Apache من XAMPP Control Panel
echo    - افتح http://localhost/mobilerechargev2/xindex.php
echo.
echo    الخيار B - استخدام PHP Built-in Server:
echo    cd mobilerechargev2 2\mobilerechargev2
echo    php -S localhost:8000
echo    افتح http://localhost:8000/xindex.php
echo.
echo 4. ربط البوت مع Telegram (Webhook أو Polling)
echo.
echo 📖 للمزيد من المعلومات: اقرأ ملف SETUP_LOCAL_SERVER.md
echo.
pause
