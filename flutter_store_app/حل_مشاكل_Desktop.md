# 🔧 حل مشاكل تطبيق Desktop على Windows

## المشكلة: PathExistsException عند تشغيل Desktop

إذا واجهت هذا الخطأ:
```
PathExistsException: Cannot create link, path = '...\ephemeral\.plugin_symlinks\file_picker'
```

## الحل السريع:

### الطريقة 1: تنظيف المشروع
```bash
cd flutter_store_app
flutter clean
flutter pub get
flutter run -d windows
```

### الطريقة 2: حذف المجلدات المشكلة يدوياً
```powershell
# في PowerShell
cd flutter_store_app
Remove-Item -Recurse -Force "windows\flutter\ephemeral" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
flutter pub get
flutter run -d windows
```

### الطريقة 3: إعادة تشغيل IDE
1. أغلق Android Studio/VS Code تماماً
2. افتح Command Prompt كمسؤول (Run as Administrator)
3. نفذ:
```bash
cd C:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app
flutter clean
flutter pub get
flutter run -d windows
```

## حلول إضافية:

### إذا استمرت المشكلة:

1. **تحقق من صلاحيات Windows:**
   - تأكد أن لديك صلاحيات الكتابة في المجلد
   - جرب تشغيل IDE كمسؤول

2. **تعطيل Windows Defender مؤقتاً:**
   - قد يمنع Windows Defender إنشاء symbolic links
   - أضف المجلد إلى الاستثناءات

3. **تفعيل Developer Mode في Windows:**
   - اذهب إلى: Settings → Update & Security → For developers
   - فعّل "Developer Mode"
   - هذا يسمح بإنشاء symbolic links بدون صلاحيات إدارية

4. **إعادة تثبيت Flutter plugins:**
```bash
cd flutter_store_app
flutter clean
flutter pub cache repair
flutter pub get
```

## التحقق من الحل:

بعد تطبيق الحل، يجب أن ترى:
- ✅ بناء المشروع بنجاح
- ✅ فتح نافذة التطبيق
- ✅ شاشة تسجيل الدخول تظهر

## ملاحظات:

- هذه المشكلة شائعة على Windows بسبب قيود symbolic links
- الحل الأفضل هو تفعيل Developer Mode
- إذا استمرت المشكلة، استخدم Android/iOS بدلاً من Desktop
