# 🚀 دليل البناء والتشغيل - Flutter Store App with PostgreSQL

## المتطلبات الأساسية
- Flutter SDK 3.10.3 أو أحدث
- Dart 3.10.3 أو أحدث
- Windows 10/11 (لـ Windows desktop)
- متغيرات البيئة مضبوطة (Flutter, Dart في PATH)

## متغيرات البيئة المطلوبة
أنشئ ملف `.env` في جذر المشروع بالقيم التالية:

```
# .env file
POSTGRES_HOST=switchback.proxy.rlwy.net
POSTGRES_DATABASE=railway
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=<your-password>
POSTGRES_PORT=20266
POSTGRES_SSL=true
```

**للحصول على بيانات الاتصال**:
1. انتقل إلى Railway Dashboard
2. افتح project "TelegramStoreBot"
3. اختر PostgreSQL service
4. انسخ بيانات الاتصال من الـ Environment tab

## خطوات البناء والتشغيل

### 1️⃣ تثبيت الاعتماديات
```bash
cd c:\Users\Hp\Desktop\TelegramStoreBot\flutter_store_app
flutter clean
flutter pub get
```

### 2️⃣ التحقق من الأخطاء (اختياري)
```bash
flutter analyze
```
**النتيجة المتوقعة**: 
- ✅ No errors
- ⚠️ بعض التحذيرات حول print statements (آمنة للتجاهل)

### 3️⃣ تشغيل التطبيق (Windows Desktop)
```bash
flutter run -d windows
```

أو للبناء فقط بدون تشغيل:
```bash
flutter build windows --release
```

### 4️⃣ تشغيل التطبيق المبني
بعد البناء الناجح، التطبيق الذي تم بناؤه يقع في:
```
build/windows/runner/Release/flutter_store_app.exe
```

---

## التحقق من التشغيل الناجح

✅ **النشاط الذي يجب أن تراه**:
1. شاشة البداية تظهر
2. اتصال PostgreSQL يتم إنشاؤه (شاهد console logs)
3. البيانات من السحابة يتم سحبها
4. تطبيق يعمل بدون أخطاء

⚠️ **في حالة الأخطاء**:

#### خطأ: "PostgreSQL connection failed"
```
✓ تحقق من متغيرات البيئة في .env
✓ تحقق من اتصال الإنترنت
✓ تحقق من صحة بيانات الاتصال
```

#### خطأ: "Compilation errors"
```
flutter clean
flutter pub get
flutter run -d windows
```

#### خطأ: "No devices available"
```
تأكد من تشغيل Windows والجهاز متصل
flutter devices
```

---

## تفاصيل المعمارية

### البنية الحالية:
- **Backend**: PostgreSQL Cloud (Railway)
- **Frontend**: Flutter Desktop (Windows)
- **وسيط البيانات**: `DatabaseHelper` wrapper
- **الخدمات**:
  - `PostgresService`: اتصال مباشر بـ PostgreSQL
  - `DatabaseHelperCloud`: عمليات CRUD السحابية
  - `SyncService`: مزامنة البيانات (Pull/Push)

### تدفق البيانات:
```
UI Screen 
  ↓
DatabaseHelper (Wrapper)
  ↓
DatabaseHelperCloud
  ↓
PostgresService
  ↓
PostgreSQL (Railway Cloud)
```

---

## الملفات الرئيسية

```
flutter_store_app/
├── lib/
│   ├── main.dart                           # نقطة الدخول
│   ├── database/
│   │   ├── database_helper.dart           # Wrapper (الواجهة الرئيسية)
│   │   ├── database_helper_cloud.dart     # تنفيذ السحابة
│   │   └── postgres_service.dart          # اتصال PostgreSQL
│   ├── services/
│   │   ├── sync_service.dart              # مزامنة البيانات
│   │   └── server_config.dart             # إعدادات الاتصال
│   ├── screens/                            # شاشات التطبيق
│   └── models/                             # نماذج البيانات
├── pubspec.yaml                            # الاعتماديات
├── .env                                    # متغيرات البيئة
└── build/
    └── windows/runner/Release/             # التطبيق المبني
```

---

## الاختبار السريع

بعد التشغيل الناجح، جرب:

1. **تحميل البيانات من السحابة**:
   - انقر على refresh
   - تحقق من أن البيانات من السحابة تظهر

2. **إضافة منتج محلي**:
   - أضف منتج جديد
   - انقر على sync
   - تحقق من أنه يظهر في السحابة

3. **مزامنة الصور**:
   - أضف صورة لمنتج
   - انقر على sync images
   - تحقق من أن الصورة تُرفع إلى السحابة

---

## استكشاف الأخطاء

### Console Logs
في أثناء التشغيل، ستراها logs:
```
🔄 Sync Timer Started (15 min interval)
☁️ Starting Startup Sync (Pull All & Prune)...
⬇️ Pulling Sellers (Prune: true)...
✅ Startup Sync Completed!
```

### التصحيح
لتمكين سجل تصحيح مفصل:
```bash
flutter run -d windows -v
```

---

## الملاحظات الهامة

⚠️ **لا تنسى**:
1. ملف `.env` يجب أن يكون في جذر المشروع
2. بيانات PostgreSQL يجب أن تكون صحيحة
3. الإنترنت يجب أن يكون متاحاً للاتصال بالسحابة
4. التطبيق يتطلب Windows 10/11

✅ **النسخة الحالية**:
- Build Name: 1.0.0
- Build Number: 1
- SDK: Flutter 3.10.3
- Database: PostgreSQL (Cloud)
- Status: ✅ Production Ready

---

**تاريخ التحديث**: 2025-01-15
**آخر إصلاح**: إصلاح أخطاء الترجمة ودعم PostgreSQL الكامل
