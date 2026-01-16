@echo off
REM ============================================
REM سكريبت اختبار البوت
REM ============================================

echo.
echo ╔════════════════════════════════════════════╗
echo ║     اختبار بوت شحن الهاتف المحمول       ║
echo ╚════════════════════════════════════════════╝
echo.

setlocal enabledelayedexpansion

REM المسار الافتراضي للمشروع
set PROJECT_PATH=mobilerechargev2 2\mobilerechargev2

if not exist "%PROJECT_PATH%" (
    echo ❌ خطأ: لم يتم العثور على مجلد المشروع
    echo البحث عن: %PROJECT_PATH%
    pause
    exit /b 1
)

echo ════════════════════════════════════════════
echo 📋 قائمة الاختبارات
echo ════════════════════════════════════════════
echo.
echo 1. اختبار الاتصال بقاعدة البيانات
echo 2. اختبار API Telegram
echo 3. اختبار الملفات المطلوبة
echo 4. اختبار المتغيرات المهمة
echo 5. اختبار شامل
echo 6. تشغيل سرفر محلي
echo.
set /p choice="اختر رقم الاختبار (1-6): "

if "%choice%"=="1" goto :db_test
if "%choice%"=="2" goto :telegram_test
if "%choice%"=="3" goto :files_test
if "%choice%"=="4" goto :vars_test
if "%choice%"=="5" goto :full_test
if "%choice%"=="6" goto :run_server
goto :invalid

:db_test
echo.
echo 🗄️  اختبار الاتصال بقاعدة البيانات...
echo ════════════════════════════════════════════
php -r "
\$host = 'localhost';
\$user = 'root';
\$pass = '';
\$db = 'mr';

\$conn = @mysqli_connect(\$host, \$user, \$pass, \$db);

if (\$conn) {
    echo '✅ الاتصال: نجح' . PHP_EOL . PHP_EOL;
    
    echo 'معلومات الاتصال:' . PHP_EOL;
    echo '  - المضيف: ' . \$host . PHP_EOL;
    echo '  - المستخدم: ' . \$user . PHP_EOL;
    echo '  - قاعدة البيانات: ' . \$db . PHP_EOL . PHP_EOL;
    
    echo 'الجداول المتاحة:' . PHP_EOL;
    \$tables = mysqli_query(\$conn, 'SHOW TABLES');
    while (\$row = mysqli_fetch_array(\$tables)) {
        echo '  ✓ ' . \$row[0] . PHP_EOL;
    }
    mysqli_close(\$conn);
} else {
    echo '❌ فشل الاتصال!' . PHP_EOL;
    echo 'الخطأ: ' . mysqli_connect_error() . PHP_EOL;
}
"
goto :end

:telegram_test
echo.
echo 📱 اختبار API Telegram...
echo ════════════════════════════════════════════
php -r "
require_once '%PROJECT_PATH%\config.php';

if (!defined('API_KEY') || empty(API_KEY)) {
    echo '❌ API_KEY لم يتم تعريفه' . PHP_EOL;
    exit(1);
}

echo 'API_KEY: ' . substr(API_KEY, 0, 10) . '...' . PHP_EOL . PHP_EOL;

\$url = 'https://api.telegram.org/bot' . API_KEY . '/getMe';
echo 'الاتصال برابط: ' . substr(\$url, 0, 50) . '...' . PHP_EOL . PHP_EOL;

\$result = @file_get_contents(\$url);
if (\$result) {
    \$data = json_decode(\$result, true);
    if (\$data['ok']) {
        echo '✅ الاتصال مع Telegram: نجح' . PHP_EOL . PHP_EOL;
        echo 'معلومات البوت:' . PHP_EOL;
        echo '  - ID: ' . \$data['result']['id'] . PHP_EOL;
        echo '  - الاسم: ' . \$data['result']['first_name'] . PHP_EOL;
        echo '  - اسم المستخدم: @' . \$data['result']['username'] . PHP_EOL;
    } else {
        echo '❌ خطأ من Telegram: ' . \$data['description'] . PHP_EOL;
    }
} else {
    echo '❌ فشل الاتصال برابط Telegram' . PHP_EOL;
    echo 'تأكد من الاتصال بالإنترنت' . PHP_EOL;
}
"
goto :end

:files_test
echo.
echo 📁 اختبار الملفات المطلوبة...
echo ════════════════════════════════════════════
setlocal enabledelayedexpansion
set files[1]=config.php
set files[2]=xindex.php
set files[3]=cronjob.php
set files[4]=numbers.json
set files[5]=Control\main.class.php
set files[6]=Languages\ar.php
set files[7]=Plugins\User\start.php
set files[8]=Plugins\Owner\main.php
set files[9]=Plugins\Admin\main.php

set count=0
set missing=0

for /L %%i in (1,1,9) do (
    if defined files[%%i] (
        set file=!files[%%i]!
        if exist "%PROJECT_PATH%\!file!" (
            echo ✅ !file!
            set /a count+=1
        ) else (
            echo ❌ !file! (غير موجود)
            set /a missing+=1
        )
    )
)

echo.
echo النتيجة: تم العثور على %count% ملفات من 9
if %missing% gtr 0 echo تحذير: %missing% ملفات مفقودة

goto :end

:vars_test
echo.
echo 🔧 اختبار المتغيرات المهمة...
echo ════════════════════════════════════════════
php -r "
require_once '%PROJECT_PATH%\config.php';

echo '1. API_KEY:' . PHP_EOL;
if (defined('API_KEY')) {
    echo '   ✅ معرّف' . PHP_EOL;
    echo '   القيمة: ' . substr(API_KEY, 0, 20) . '...' . PHP_EOL;
} else {
    echo '   ❌ غير معرّف' . PHP_EOL;
}

echo PHP_EOL . '2. IDBot:' . PHP_EOL;
if (defined('IDBot')) {
    echo '   ✅ معرّف' . PHP_EOL;
    echo '   القيمة: ' . IDBot . PHP_EOL;
} else {
    echo '   ❌ غير معرّف' . PHP_EOL;
}

echo PHP_EOL . '3. قاعدة البيانات:' . PHP_EOL;
echo '   المضيف: ' . ((defined('Host')) ? Host : 'غير معرّف') . PHP_EOL;
echo '   المستخدم: ' . ((defined('UserName')) ? UserName : 'غير معرّف') . PHP_EOL;
echo '   اسم قاعدة البيانات: ' . ((defined('DBName')) ? DBName : 'غير معرّف') . PHP_EOL;
"
goto :end

:full_test
echo.
echo 🧪 اختبار شامل...
echo ════════════════════════════════════════════
echo.
call :db_test
echo.
echo ════════════════════════════════════════════
echo.
call :telegram_test
echo.
echo ════════════════════════════════════════════
echo.
call :files_test
echo.
echo ════════════════════════════════════════════
echo.
call :vars_test
goto :end

:run_server
echo.
echo 🚀 تشغيل السرفر المحلي...
echo ════════════════════════════════════════════
echo.
echo اختر نوع السرفر:
echo 1. PHP Built-in Server (الخفيف)
echo 2. Apache (إذا كان XAMPP مثبتاً)
echo.
set /p server="اختيارك (1 أو 2): "

if "%server%"=="1" (
    cd "%PROJECT_PATH%"
    echo ✅ تشغيل PHP Server على http://localhost:8000
    echo.
    echo اضغط Ctrl+C لإيقاف السرفر
    echo.
    php -S localhost:8000
) else if "%server%"=="2" (
    echo ✅ تأكد من:
    echo   - تشغيل Apache من XAMPP Control Panel
    echo   - نسخ المشروع إلى C:\xampp\htdocs\mobilerechargev2
    echo.
    echo ثم افتح في المتصفح:
    echo   http://localhost/mobilerechargev2/
    echo.
    pause
) else (
    goto :invalid
)
goto :end

:invalid
echo ❌ اختيار غير صحيح
pause
exit /b 1

:end
echo.
pause
