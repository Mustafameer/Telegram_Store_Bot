# تعليمات تطبيق Migration لحل مشكلة "Integer out of range"

## المشكلة
عند الدخول عبر رابط المتجر أو إضافة منتجات للسلة، تظهر رسالة "Integer out of range" لأن قاعدة البيانات PostgreSQL تستخدم `INTEGER` بدلاً من `BIGINT` لحفظ Telegram IDs الكبيرة.

## الحل: تطبيق Migration يدوياً

### الخطوة 1: فتح قاعدة البيانات PostgreSQL

1. اذهب إلى [Railway Dashboard](https://railway.app)
2. اختر المشروع الخاص بك
3. اذهب إلى قاعدة البيانات PostgreSQL
4. اضغط على "Query" أو "SQL Editor" أو "Connect"

### الخطوة 2: تطبيق Migration

انسخ والصق الأوامر التالية في SQL Editor واضغط Run:

```sql
-- تطبيق Migration بشكل إجباري
ALTER TABLE Users ALTER COLUMN TelegramID TYPE BIGINT;
ALTER TABLE Sellers ALTER COLUMN TelegramID TYPE BIGINT;
ALTER TABLE CreditCustomers ALTER COLUMN TelegramID TYPE BIGINT;
ALTER TABLE Orders ALTER COLUMN BuyerID TYPE BIGINT;
ALTER TABLE Carts ALTER COLUMN UserID TYPE BIGINT;
```

### الخطوة 3: التحقق من النجاح

نفّذ هذا الأمر للتحقق:

```sql
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE column_name IN ('telegramid', 'buyerid', 'userid')
    AND table_name IN ('users', 'sellers', 'creditcustomers', 'orders', 'carts')
ORDER BY table_name, column_name;
```

يجب أن تكون جميع `data_type` هي `bigint`.

### الخطوة 4: إعادة تشغيل البوت

بعد تطبيق Migration:
1. اذهب إلى Railway Dashboard
2. اضغط على "Redeploy" للبوت
3. انتظر حتى يكتمل الـ Redeploy

### الخطوة 5: اختبار الحل

1. افتح رابط متجر من موبايل مشتري
2. يجب أن تظهر الأزرار تلقائياً
3. يجب أن تعمل إضافة المنتجات للسلة بدون أخطاء
4. يجب أن تختفي رسالة "Integer out of range"

## ملاحظات مهمة

- **لا تقلق**: تطبيق Migration آمن ولن يفقد البيانات
- **النسخ الاحتياطي**: Railway يقوم بعمل نسخ احتياطي تلقائياً
- **إذا فشل Migration**: تحقق من أنك تستخدم قاعدة البيانات الصحيحة

## إذا استمرت المشكلة

إذا استمرت المشكلة بعد تطبيق Migration:

1. تحقق من سجلات البوت (Logs) في Railway
2. ابحث عن رسائل Migration:
   - `🔍 Checking Users.TelegramID column type...`
   - `🔄 FORCE Migrating...`
   - `✅ migrated to BIGINT successfully`
3. إذا لم تظهر هذه الرسائل، Migration لم يتم تطبيقه

## الدعم

إذا واجهت أي مشاكل، أرسل:
1. لقطة شاشة من SQL Editor بعد تنفيذ Migration
2. لقطة شاشة من نتائج التحقق (الخطوة 3)
3. أي رسائل خطأ تظهر في سجلات البوت
