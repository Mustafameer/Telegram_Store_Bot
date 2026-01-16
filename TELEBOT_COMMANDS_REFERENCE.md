# 🔧 أوامر مهمة لإدارة نظام TELEBOT

## 🚀 تشغيل الأدوات

### 1. إضافة متجر TELEBOT (إذا لم يكن موجوداً)
```bash
python add_telebot_store.py
```

### 2. اختبار النظام
```bash
python test_telebot_system.py
```

### 3. تشغيل البوت
```bash
python bot.py
```

---

## 💾 أوامر قاعدة البيانات

### عرض جميع المتاجر مع حالتها
```sql
SELECT SellerID, StoreName, UserName, RequireCustomerRegistration as Status
FROM Sellers
ORDER BY StoreName;
```

### عرض المتاجر المقفولة فقط
```sql
SELECT SellerID, StoreName, UserName
FROM Sellers
WHERE RequireCustomerRegistration = 1 AND Status = 'active'
ORDER BY StoreName;
```

### عرض المتاجر المفتوحة فقط
```sql
SELECT SellerID, StoreName, UserName
FROM Sellers
WHERE (RequireCustomerRegistration = 0 OR RequireCustomerRegistration IS NULL) AND Status = 'active'
ORDER BY StoreName;
```

### تحويل متجر من مفتوح إلى مقفول
```sql
UPDATE Sellers 
SET RequireCustomerRegistration = 1 
WHERE SellerID = <ID>;
```

### تحويل متجر من مقفول إلى مفتوح
```sql
UPDATE Sellers 
SET RequireCustomerRegistration = 0 
WHERE SellerID = <ID>;
```

### عرض منتجات المتاجر المقفولة
```sql
SELECT DISTINCT 
    p.ProductID, 
    p.Name, 
    p.Price, 
    s.StoreName
FROM Products p
JOIN Sellers s ON p.SellerID = s.SellerID
WHERE s.RequireCustomerRegistration = 1 
  AND s.Status = 'active' 
  AND p.Status = 'active'
ORDER BY s.StoreName, p.Name;
```

### عد منتجات كل متجر مقفول
```sql
SELECT 
    s.StoreName,
    COUNT(p.ProductID) as product_count
FROM Sellers s
LEFT JOIN Products p ON s.SellerID = p.SellerID AND p.Status = 'active'
WHERE s.RequireCustomerRegistration = 1 AND s.Status = 'active'
GROUP BY s.SellerID, s.StoreName
ORDER BY s.StoreName;
```

---

## 📊 الإحصائيات المهمة

### عدد المتاجر المقفولة
```sql
SELECT COUNT(*) as closed_stores
FROM Sellers
WHERE RequireCustomerRegistration = 1 AND Status = 'active';
```

### عدد منتجات المتاجر المقفولة
```sql
SELECT COUNT(DISTINCT p.ProductID) as closed_store_products
FROM Products p
JOIN Sellers s ON p.SellerID = s.SellerID
WHERE s.RequireCustomerRegistration = 1 AND s.Status = 'active' AND p.Status = 'active';
```

### التوزيع الكامل للمتاجر
```sql
SELECT 
    CASE 
        WHEN RequireCustomerRegistration = 1 THEN 'مقفول'
        ELSE 'مفتوح'
    END as store_type,
    COUNT(*) as count
FROM Sellers
WHERE Status = 'active'
GROUP BY RequireCustomerRegistration;
```

---

## 🔐 فحوصات الأمان والسلامة

### التحقق من وجود متجر TELEBOT
```sql
SELECT * FROM Sellers WHERE UserName = 'telebot';
```

### التحقق من عدم وجود تكرار TelegramID
```sql
SELECT TelegramID, COUNT(*) as count
FROM Sellers
GROUP BY TelegramID
HAVING COUNT(*) > 1;
```

### التحقق من صحة جميع الصور
```sql
SELECT p.ProductID, p.Name, p.ImagePath
FROM Products p
LEFT JOIN ImageStorage i ON p.ImagePath = i.FileName
WHERE p.Status = 'active' AND i.FileName IS NULL
LIMIT 10;
```

---

## 🧪 سيناريوهات الاختبار

### السيناريو 1: اختبار متجر TELEBOT مع متجر مقفول
```bash
# 1. افتح قاعدة البيانات
# 2. نفذ:
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;

# 3. شغل:
python test_telebot_system.py

# 4. النتيجة المتوقعة:
# - المتاجر المقفولة: 1
# - منتجات المتاجر المقفولة: (عدد منتجات المتجر 5)
```

### السيناريو 2: اختبار إضافة منتج إلى متجر مقفول
```sql
-- 1. أضف متجر مقفول
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;

-- 2. أضف منتج جديد
INSERT INTO Products (SellerID, CategoryID, Name, Price, Quantity, Status)
VALUES (5, 1, 'منتج اختبار جديد', 5000, 100, 'active');

-- 3. تحقق من ظهور المنتج في TELEBOT
-- (اختبر في البوت: اختر TELEBOT ويجب أن تري المنتج الجديد)
```

### السيناريو 3: تحويل متجر من مقفول إلى مفتوح
```sql
-- 1. كان المتجر مقفول
-- RequireCustomerRegistration = 1

-- 2. افتحه
UPDATE Sellers SET RequireCustomerRegistration = 0 WHERE SellerID = 5;

-- 3. تحقق من اختفاء منتجاته من TELEBOT
-- (اختبر في البوت: متجر 5 يجب أن لا يظهر في TELEBOT)
```

---

## ⚠️ نصائح مهمة

### الحذر من:
1. ❌ **تعديل TelegramID لمتجر TELEBOT** → قد يحطم النظام
2. ❌ **حذف متجر TELEBOT** → سيتسبب في خطأ
3. ❌ **تغيير StoreName لـ TELEBOT** → قد يرتبك المستخدمون

### أفضل الممارسات:
1. ✅ **اختبر التغييرات أولاً** قبل النشر
2. ✅ **احفظ نسخة احتياطية** قبل التعديلات الكبيرة
3. ✅ **استخدم test_telebot_system.py** بعد أي تغيير

---

## 🆘 استكشاف الأخطاء

### المشكلة: لا يظهر متجر TELEBOT
**الحل**:
```bash
# 1. تحقق من وجود TELEBOT
python test_telebot_system.py

# 2. إذا لم يكن موجود، أضفه:
python add_telebot_store.py

# 3. أعد تشغيل البوت
python bot.py
```

### المشكلة: لا تظهر منتجات المتاجر المقفولة
**الحل**:
```bash
# 1. تحقق من وجود متاجر مقفولة
python test_telebot_system.py

# 2. إذا كان 0، جعل متجر مقفول:
UPDATE Sellers SET RequireCustomerRegistration = 1 WHERE SellerID = 5;

# 3. أضف منتجات للمتجر إذا لزم الأمر
# 4. أعد تشغيل البوت واختبره
```

### المشكلة: الصور لا تظهر في TELEBOT
**الحل**:
```bash
# 1. تحقق من وجود الصور في ImageStorage
SELECT COUNT(*) FROM ImageStorage;

# 2. تحقق من صحة أسماء الملفات
SELECT ImagePath FROM Products WHERE ImagePath IS NOT NULL LIMIT 5;

# 3. تأكد من أن image_path صحيح في جدول Products
```

---

## 📝 قائمة الفحص اليومية

- [ ] هل متجر TELEBOT نشط؟ (`python test_telebot_system.py`)
- [ ] هل جميع المتاجر لها الحالة الصحيحة؟ (مفتوح/مقفول)
- [ ] هل هناك متاجر معلقة تحتاج إلى متابعة؟
- [ ] هل جميع الصور موجودة في ImageStorage؟
- [ ] هل البوت يعمل بدون أخطاء؟

---

## 📞 أرقام مرجعية

| البيان | القيمة |
|--------|--------|
| TELEBOT SellerID | 27 |
| TELEBOT TelegramID | 999999999 |
| TELEBOT UserName | telebot |
| قاعدة البيانات | Railway PostgreSQL |

---

**آخر تحديث**: 15 يناير 2026
