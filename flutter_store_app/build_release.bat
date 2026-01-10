@echo off
chcp 65001 >nul
echo ============================================
echo   بناء تطبيق Flutter Store App
echo ============================================
echo.

:: الانتقال إلى مجلد المشروع
cd /d "%~dp0"

:: التحقق من وجود Flutter
where flutter >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ خطأ: Flutter غير موجود في PATH
    echo    يرجى التأكد من تثبيت Flutter وإضافته إلى PATH
    pause
    exit /b 1
)

:: تنظيف المشروع
echo [1/4] تنظيف المشروع...
call flutter clean
if %ERRORLEVEL% NEQ 0 (
    echo ❌ فشل تنظيف المشروع
    pause
    exit /b 1
)

:: تثبيت التبعيات
echo [2/4] تثبيت التبعيات...
call flutter pub get
if %ERRORLEVEL% NEQ 0 (
    echo ❌ فشل تثبيت التبعيات
    pause
    exit /b 1
)

:: بناء التطبيق في وضع Release
echo [3/5] بناء التطبيق (Release)...
call flutter build windows --release
if %ERRORLEVEL% NEQ 0 (
    echo ❌ فشل بناء التطبيق
    pause
    exit /b 1
)

:: تثبيت ملفات البيانات (data folder) - مطلوب لتشغيل التطبيق
echo [4/5] تثبيت ملفات البيانات...
cd build\windows\x64
cmake --install . --config Release
cd ..\..\..
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  تحذير: فشل تثبيت ملفات البيانات، لكن سنتابع...
)

:: التحقق من وجود ملف .exe ومجلد data
if not exist "build\windows\x64\runner\Release\flutter_store_app.exe" (
    echo ❌ خطأ: لم يتم العثور على ملف .exe بعد البناء
    pause
    exit /b 1
)

if not exist "build\windows\x64\runner\Release\data" (
    echo ⚠️  تحذير: مجلد data غير موجود - جاري نسخ ملفات البيانات...
    if not exist "build\windows\x64\runner\Release\data" mkdir "build\windows\x64\runner\Release\data"
    
    :: نسخ flutter_assets
    if exist "build\flutter_assets" (
        xcopy /E /I /Y "build\flutter_assets" "build\windows\x64\runner\Release\data\flutter_assets"
        echo ✅ تم نسخ flutter_assets
    )
    
    :: نسخ icudtl.dat
    if exist "windows\flutter\ephemeral\icudtl.dat" (
        copy /Y "windows\flutter\ephemeral\icudtl.dat" "build\windows\x64\runner\Release\data\icudtl.dat"
        echo ✅ تم نسخ icudtl.dat
    )
    
    :: نسخ app.so
    if exist "build\windows\app.so" (
        copy /Y "build\windows\app.so" "build\windows\x64\runner\Release\data\app.so"
        echo ✅ تم نسخ app.so
    )
    
    if exist "build\windows\x64\runner\Release\data\flutter_assets" (
        echo ✅ تم إنشاء مجلد data بنجاح
    ) else (
        echo ❌ فشل إنشاء مجلد data - التطبيق قد لا يعمل
    )
)

echo.
echo ✅ تم بناء التطبيق بنجاح!
echo.
echo ============================================
echo   إنشاء ملف التثبيت باستخدام Inno Setup
echo ============================================
echo.

:: التحقق من وجود Inno Setup
set INNO_SETUP_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set INNO_SETUP_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
) else (
    echo ⚠️  تحذير: لم يتم العثور على Inno Setup
    echo    يرجى تثبيت Inno Setup من: https://jrsoftware.org/isdl.php
    echo    أو قم بتشغيل build_installer.iss يدوياً من Inno Setup Compiler
    pause
    exit /b 1
)

:: إنشاء مجلد installer إذا لم يكن موجوداً
if not exist "installer" mkdir installer

:: تشغيل Inno Setup Compiler
echo [5/5] إنشاء ملف التثبيت...
pushd "%~dp0"
"%INNO_SETUP_PATH%" "%~dp0build_installer.iss"
popd
if %ERRORLEVEL% NEQ 0 (
    echo ❌ فشل إنشاء ملف التثبيت
    pause
    exit /b 1
)

echo.
echo ✅ تم إنشاء ملف التثبيت بنجاح!
echo    الموقع: installer\TelegramStoreApp_Setup.exe
echo.
pause
