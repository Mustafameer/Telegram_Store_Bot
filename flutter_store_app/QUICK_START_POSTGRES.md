# Flutter Desktop + PostgreSQL Cloud - إعداد سريع

## 🚀 الخطوات الأولى

### 1️⃣ تحديث المكتبات
```bash
cd flutter_store_app
flutter pub get
```

### 2️⃣ إنشاء ملف الإعدادات
انسخ الملف `.env.example` إلى `.env`:
```bash
cp .env.example .env
```

### 3️⃣ إضافة بيانات الاتصال بـ Railway
عدّل `.env` وأضف:
```env
DATABASE_URL=postgresql://user:password@switchback.proxy.rlwy.net:20266/railway?sslmode=require
```

> **حيث**:
> - `user` = اسم المستخدم (عادة `postgres`)
> - `password` = كلمة المرور من Railway
> - `switchback.proxy.rlwy.net:20266` = معرّف الخادم والمنفذ من Railway

### 4️⃣ تشغيل التطبيق
```bash
flutter run -d windows
```

## 📋 التحقق من النجاح

عند البدء، يجب أن تشاهد في Terminal:
```
✅ Loaded .env file
✅ PostgreSQL connection initialized  
✅ Connected to PostgreSQL Cloud Database
```

إذا حدث خطأ في الاتصال، تحقق من:
1. ملف `.env` موجود والبيانات صحيحة
2. الإنترنت متصل
3. خادم Railway يعمل

## 🔄 كيف يعمل

| العملية | كيف تعمل |
|---------|----------|
| **قراءة المنتجات** | مباشرة من PostgreSQL |
| **إنشاء طلب** | يُحفظ في PostgreSQL |
| **تحديث الكمية** | تحديث في PostgreSQL |
| **تعديل المنتجات** | عبر البوت فقط ❌ |
| **حذف المنتجات** | عبر البوت فقط ❌ |

## 🔐 الأمان

⚠️ **لا تُقسّم كلمات المرور في الكود!**
- استخدم `.env` دائماً
- لا تُضيف `.env` إلى Git
- استخدم `git update-index --assume-unchanged .env` إذا أضفته مسبقاً

## 🐛 استكشاف المشاكل

### المشكلة: "Connection refused"
```
❌ Connection failed: Failed to connect to...
```
**الحل**: 
- تحقق من بيانات `DATABASE_URL`
- تأكد من أن Railway Server يعمل
- أعد تشغيل التطبيق

### المشكلة: "SSL error"
```
❌ SSL certificate verification failed
```
**الحل**: تأكد من:
- `sslmode=require` موجود في `DATABASE_URL`
- الإنترنت متصل وثابت

### المشكلة: "تاريخ انتهاء الشهادة"
```
❌ certificate has expired
```
**الحل**: تواصل مع Railway للحصول على شهادة جديدة

## 📞 الدعم

تحتاج مساعدة؟
- اقرأ `CLOUD_DATABASE_MIGRATION.md` للتفاصيل الكاملة
- اقرأ `IMPLEMENTATION_SUMMARY.md` لملخص التغييرات
- تحقق من السجلات (Terminal) لرسائل خطأ واضحة

---

**آخر تحديث**: 15 يناير 2026
**الحالة**: ✅ جاهز للاستخدام
