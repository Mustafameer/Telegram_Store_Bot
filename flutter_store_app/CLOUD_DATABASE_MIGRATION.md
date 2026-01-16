# تحويل تطبيق Flutter Desktop إلى قاعدة بيانات سحابية PostgreSQL

## ملخص التغييرات

تم تحويل تطبيق Flutter Desktop من استخدام قاعدة بيانات محلية SQLite إلى استخدام نفس قاعدة بيانات PostgreSQL السحابية التي يستخدمها البوت (Railway).

### الملفات المضافة

#### 1. **`lib/services/postgres_service.dart`** (جديد)
- خدمة الاتصال الكاملة بقاعدة بيانات PostgreSQL
- يقرأ بيانات الاتصال من متغيرات البيئة (`DATABASE_URL`)
- يدعم جميع العمليات:
  - الحصول على البيانات (Sellers, Categories, Products)
  - إدارة الطلبات (Orders)
  - إدارة السلة (Cart)
  - إدارة المستخدمين (Users)
  - إدارة الصور (Product Images)

#### 2. **`lib/database/database_helper_cloud.dart`** (جديد)
- تطبيق `DatabaseHelper` باستخدام `PostgresService`
- يحل محل الكود المحلي SQLite القديم
- يحافظ على نفس الواجهة (Interface) للتوافقية مع الشاشات

### الملفات المعدلة

#### 1. **`lib/database/database_helper.dart`**
- تم تبسيطه ليصبح proxy/wrapper يفوض إلى `DatabaseHelperCloud`
- يحافظ على التوافقية العكسية (Backward Compatibility)

#### 2. **`lib/main.dart`**
- إضافة تحميل متغيرات البيئة باستخدام `flutter_dotenv`
- تهيئة `PostgresService` عند بدء التطبيق
- تم إزالة معالجة SQLite المحلي

#### 3. **`pubspec.yaml`**
- إضافة المكتبات المطلوبة:
  - `postgres: ^3.4.4` - Driver PostgreSQL
  - `flutter_dotenv: ^5.2.1` - قراءة متغيرات البيئة

#### 4. **`.env.example`**
- معايير جديدة لتكوين الاتصال بـ Railway
- خيارات متعددة للاتصال (DATABASE_URL أو معايير فردية)

## كيفية الاستخدام

### 1. إعداد متغيرات البيئة

انسخ الملف `.env.example` إلى `.env`:

```bash
cp .env.example .env
```

ثم أضف بيانات الاتصال:

```env
DATABASE_URL=postgresql://user:password@switchback.proxy.rlwy.net:20266/railway?sslmode=require
```

أو استخدم المعايير الفردية:

```env
DB_HOST=switchback.proxy.rlwy.net
DB_PORT=20266
DB_NAME=railway
DB_USER=postgres
DB_PASSWORD=your_actual_password
DB_SSL=true
```

### 2. تشغيل التطبيق

```bash
flutter run -d windows
```

### 3. التحقق من الاتصال

التطبيق سيطبع رسائل في Terminal:
```
✅ Loaded .env file
✅ PostgreSQL connection initialized
✅ Connected to PostgreSQL Cloud Database
```

## هندسة النظام

```
┌─────────────────────────┐
│   Flutter UI Screens    │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│   DatabaseHelper        │ (Wrapper - للتوافقية)
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ DatabaseHelperCloud     │ (جديد - يستخدم PostgreSQL)
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ PostgresService         │ (جديد - الاتصال الفعلي)
└────────────┬────────────┘
             │
        PostgreSQL ← → Railway Server
```

## الفروقات عن النسخة القديمة

| العملية | SQLite (قديم) | PostgreSQL (جديد) |
|---------|---------------|-------------------|
| المصدر | ملف محلي | خادم سحابي Railway |
| التزامن | يدوي/غير موثوق | تلقائي مع البوت |
| التعديل | مباشرة في التطبيق | عبر البوت فقط |
| الصور | محفوظة محلياً | في السحابة + محلي |
| البيانات | معزولة | مشتركة مع البوت |

## الوظائف المدعومة

### ✅ مدعومة بالكامل
- الحصول على بيانات المنتجات والفئات والبائعين
- إنشاء الطلبات
- إدارة السلة
- الحصول على الطلبات السابقة
- الحصول على صور المنتجات

### ⚠️ مدارة عبر البوت فقط
- تعديل المنتجات والفئات والبائعين
- إدارة العملاء (Credit Customers)
- إدارة الرسائل
- حذف الطلبات

هذا بالتصميم - التطبيق يعمل كـ **عميل قراءة وإنشاء** والبوت هو **المصدر الموثوق** لجميع التعديلات.

## استكشاف الأخطاء

### خطأ: "فشل الاتصال بقاعدة البيانات"
1. تحقق من وجود ملف `.env` مع البيانات الصحيحة
2. تحقق من اتصال الإنترنت
3. تأكد من أن Railway Server يعمل
4. تحقق من تاريخ انتهاء الاتصال (Certificate expiry)

### خطأ: "رسالة: خطأ في SSL"
- تأكد من `DB_SSL=true` في `.env`
- أو استخدم `sslmode=require` في `DATABASE_URL`

### البيانات لا تتحدث تلقائياً
- التحديثات من البوت تظهر عند إعادة فتح الشاشة
- يمكن إضافة polling/subscription لاحقاً

## الخطوات التالية (اختيارية)

1. **إضافة real-time updates**: استخدام WebSocket أو Polling
2. **تحسين أداء الاتصال**: Connection pooling
3. **معالجة أفضل للأخطاء**: Retry logic
4. **تخزين مؤقت**: Caching للبيانات المتكررة
5. **مزامنة محسّنة**: Full sync protocol مثل البوت

---

تم التحويل بنجاح! التطبيق الآن يستخدم **نفس البيانات والمنطق** كالبوت.
