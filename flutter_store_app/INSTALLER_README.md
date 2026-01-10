# دليل إنشاء ملف التثبيت (Installer)

هذا الدليل يشرح كيفية إنشاء ملف تثبيت `.exe` لتطبيق Flutter Store App باستخدام Inno Setup.

## المتطلبات

1. **Flutter SDK** - يجب أن يكون مثبتاً ومضافاً إلى PATH
2. **Inno Setup 6** - يمكن تحميله من: https://jrsoftware.org/isdl.php

## خطوات الإنشاء

### الطريقة السريعة (موصى بها)

1. افتح Command Prompt أو PowerShell في مجلد المشروع (`flutter_store_app`)
2. قم بتشغيل:
   ```batch
   build_release.bat
   ```
3. انتظر حتى يكتمل البناء وإنشاء ملف التثبيت
4. سيكون ملف التثبيت موجوداً في: `installer\TelegramStoreApp_Setup.exe`

### الطريقة اليدوية

#### 1. بناء التطبيق
```batch
flutter clean
flutter pub get
flutter build windows --release
```

#### 2. إنشاء ملف التثبيت
1. افتح Inno Setup Compiler
2. افتح ملف `build_installer.iss`
3. اضغط F9 أو اختر Build > Compile
4. سيكون ملف التثبيت في مجلد `installer`

## ملفات الإخراج

- **ملف التثبيت**: `installer\TelegramStoreApp_Setup.exe`
- **مجلد البناء**: `build\windows\x64\runner\Release\`

## ملاحظات

- الأيقونة المستخدمة: `windows\runner\Release\TeleBot.ico`
- اسم التطبيق: `Telegram Store App`
- الإصدار: `1.0.0`
- يتم تثبيت التطبيق في: `C:\Program Files\Telegram Store App`

## استكشاف الأخطاء

### خطأ: Flutter غير موجود
- تأكد من تثبيت Flutter وإضافته إلى PATH
- اختبر بكتابة `flutter --version` في Command Prompt

### خطأ: Inno Setup غير موجود
- قم بتثبيت Inno Setup 6 من الموقع الرسمي
- أو قم بتشغيل `build_installer.iss` يدوياً من Inno Setup Compiler

### خطأ: ملف .exe غير موجود بعد البناء
- تأكد من أن البناء تم بنجاح بدون أخطاء
- تحقق من وجود الملف في: `build\windows\x64\runner\Release\flutter_store_app.exe`

## التخصيص

يمكنك تعديل الإعدادات التالية في ملف `build_installer.iss`:

- `AppName`: اسم التطبيق
- `AppVersion`: إصدار التطبيق
- `AppPublisher`: اسم الناشر
- `SetupIconFile`: مسار الأيقونة
